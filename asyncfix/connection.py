import asyncio
import sys
import time
from enum import IntEnum, Enum
import logging
from asyncfix import FTag, FMsg
from asyncfix.errors import FIXConnectionError
from asyncfix.codec import Codec
from asyncfix.journaler import Journaler
from asyncfix.message import FIXMessage, MessageDirection
from asyncfix.protocol import FIXProtocolBase
from asyncfix.session import FIXSession


# fmt: off
class ConnectionState(IntEnum):
    UNKNOWN = 0

    DISCONNECTED_NOCONN_TODAY = 1    # both
    """
    Currently disconnected, have not attempted to establish a connection today
    """

    DISCONNECTED_WCONN_TODAY = 2     # both
    """
    Currently disconnected, have attempted to establish a connection today
    """

    DISCONNECTED_BROKEN_CONN = 3    # both
    """
    While connected, detect a broken network connection (e.g. TCP socket closed)
    """

    AWAITING_CONNECTION = 4          # acceptor
    """
    Session acceptor Logon awaiting network connection from counterparty.
    """

    INITIATE_CONNECTION = 5          # initiator
    """
    Session initiator Logon establishing network connection with counterparty.
    """

    NETWORK_CONN_ESTABLISHED = 6     # both
    """
    Network connection established between both parties.
    """

    LOGON_INITIAL_SENT = 7           # initiator
    """
    Session initiator Logon send Logon(35=A) message.
    """

    LOGON_INITIAL_RECV = 8           # acceptor
    """
    Session acceptor Logon receive counterparty’s Logon(35=A) message.
    """

    LOGON_RESPONSE = 9               # acceptor
    """
    Session acceptor Logon respond to peer with Logon message to handshake.
    """

    HANDLE_RESENDREQ = 10            # both
    """Receive and respond to counterparty’s ResendRequest(35=2) sending requested
       messages and/or SequenceReset(35=4) gap fill messages for the range of
       MsgSeqNum(34) requested."""

    RECV_SEQNUM_TOO_HIGH = 11        # both
    """Receive too high of MsgSeqNum(34) from counterparty, queue message,
       and send ResendRequest(35=2)."""

    RESEND_REQ_PROCESSING = 12       # both
    """Process requested MsgSeqNum(34) with PossDupFlag(43)=Y resent messages and/or
       SequenceReset(35=4) gap fill messages from counterparty. """

    NO_MSG_IN_INTERVAL = 13          # both
    """
    No inbound messages (non-garbled) received in (HeartBtInt+ reasonable time
    """

    AWAIT_PROC_TEST_REQ = 14         # both
    """Process inbound messages. Reset heartbeat interval-related timer when ANY
       inbound message (non-garbled) is received."""

    RECEIVED_LOGOUT = 15             # both
    """
    Receive Logout(35=5) message from counterparty initiating logout/disconnect.
    """

    INITIATE_LOGOUT = 16             # both
    """	Identify condition or reason to gracefully disconnect (e.g. end of “day”,
    no response after multiple TestRequest(35=1) messages, too low MsgSeqNum(34))"""

    ACTIVE = 17                      # both
    """
    Network connection established, Logon(35=A) message exchange completed.
    """

    WAITING_FOR_LOGON = 18           # initiator
    """
    Session initiator waiting for session acceptor to send back a Logon(35=A)
    """
# fmt: on


class ConnectionRole(Enum):
    UNKNOWN = 0
    INITIATOR = 1
    ACCEPTOR = 2


class AsyncFIXConnection:
    def __init__(
        self,
        protocol: FIXProtocolBase,
        sender_comp_id: str,
        target_comp_id: str,
        journaler: Journaler,
        host: str,
        port: int,
        heartbeat_period: int = 30,
        logger: logging.Logger | None = None,
        start_tasks: bool = True,
    ):
        self.codec = Codec(protocol)
        self.sender_comp_id = sender_comp_id
        self.target_comp_id = target_comp_id
        self.connection_state = ConnectionState.DISCONNECTED_NOCONN_TODAY
        self.connection_role = ConnectionRole.UNKNOWN
        self.journaler = journaler
        self.session: FIXSession = journaler.create_or_load(
            target_comp_id, sender_comp_id
        )
        self.msg_buffer = b""
        self.heartbeat_period = heartbeat_period
        self.message_last_time = 0.0
        self.socket_reader = None
        self.socket_writer = None
        self.host = host
        self.port = port
        if not logger:
            self.log = logging.getLogger()
        else:
            self.log = logger

        if start_tasks:
            asyncio.create_task(self.socket_read_task())
            asyncio.create_task(self.heartbeat_timer_task())

    @property
    def protocol(self) -> FIXProtocolBase:
        return self.codec.protocol

    async def connect(self):
        raise NotImplementedError("connect() is not implemented in child")

    async def disconnect(
        self, disconn_state: ConnectionState, logout_message: str = None
    ):
        if self.connection_state > ConnectionState.DISCONNECTED_BROKEN_CONN:
            assert disconn_state <= ConnectionState.DISCONNECTED_BROKEN_CONN

            if logout_message is not None:
                msg = self.protocol.logout()
                msg[FTag.Text] = logout_message
                await self.send_msg(msg)

            self.log.info(f"Client disconnected, with state: {repr(disconn_state)}")
            if self.socket_writer:
                self.socket_writer.close()
                await self.socket_writer.wait_closed()
            self.socket_writer = None
            self.socket_reader = None
            self.connection_state = disconn_state
            await self.on_disconnect()

    async def reset_seq_num(self):
        self.session.reset_seq_num()
        self.journaler.set_seq_nums(self.session)

    async def socket_read_task(self):
        while True:
            try:
                if not self.socket_reader:
                    # Socket was not connected, just wait
                    await asyncio.sleep(1)
                    continue

                msg = await self.socket_reader.read(4096)
                if not msg:
                    raise ConnectionError

                self.msg_buffer = self.msg_buffer + msg
                while True:
                    if self.connection_state == ConnectionState.DISCONNECTED:
                        break

                    (decoded_msg, parsed_length, raw_msg) = self.codec.decode(
                        self.msg_buffer
                    )
                    # logging.debug(decoded_msg)

                    if parsed_length > 0:
                        self.msg_buffer = self.msg_buffer[parsed_length:]

                    if decoded_msg is None:
                        break

                    await self._process_message(decoded_msg, raw_msg)
            except asyncio.CancelledError:
                raise
            except ConnectionError as why:
                logging.debug("Connection has been closed %s" % (why,))
                await self.disconnect()
                continue
            except Exception:
                logging.exception("handle_read exception")
                # raise

    async def heartbeat_timer_task(self):
        while True:
            try:
                if not self.socket_writer or not self.socket_reader:
                    # Socket was not connected, just wait
                    await asyncio.sleep(1)
                    continue

                if self.connection_state == ConnectionState.LOGGED_IN:
                    if time.time() - self.message_last_time > self.heartbeat_period - 1:
                        await self.send_msg(self.protocol.heartbeat())
                        self.message_last_time = time.time()

            except asyncio.CancelledError:
                raise
            except Exception:
                logging.exception("heartbeat_timer() error")
            await asyncio.sleep(1.0)

    async def on_message(self, msg: FIXMessage):
        pass

    async def on_connect(self):
        pass

    async def on_disconnect(self):
        pass

    async def on_logon(self, msg: FIXMessage):
        pass

    async def on_logout(self, msg: FIXMessage):
        pass

    def _validate_intergity(self, msg: FIXMessage) -> bool:
        # TODO: validate tag=BeginString(8) == protocol.beginstring

        # TODO: validate SenderCompID/TargetCompID match

        # TODO: validate SendingTime ~~ within 2x heartbeat_period
        return True
        pass

    async def _process_logon(self, msg: FIXMessage):
        assert msg.msg_type == FMsg.LOGON
        assert (
            self.connection_role == ConnectionRole.ACCEPTOR
            or self.connection_role == ConnectionRole.INITIATOR
        )

        msg_seq_num = int(msg[FTag.MsgSeqNum])

        if self.connection_role == ConnectionRole.INITIATOR:
            pass
        elif self.connection_role == ConnectionRole.ACCEPTOR:
            assert self.connection_state == ConnectionState.LOGON_INITIAL_RECV
            if msg_seq_num >= self.session.next_num_in:
                await self.send_msg(self.protocol.logon())

        # TODO: figure out MsgSeqNum and request backfill?
        if msg_seq_num == self.session.next_num_in:
            # https://www.fixtrading.org/standards/fix-session-layer-online/#establishing-a-fix-connection
            # The initiator and acceptor should wait a short period of time following
            # receipt of the Logon(35=A) message from the counterparty before
            # transmitting queued or new application messages to permit both sides
            # to synchronize the FIX session.
            # await asyncio.sleep(1.0)
            self.connection_state = ConnectionState.ACTIVE
            # TODO: decide send extra test request?
            await self.on_logon(msg)
        elif msg_seq_num > self.session.next_num_in:
            # TODO: request gap fill
            assert False, f"TODO: gap fill, {msg_seq_num=} {self.session.next_num_in=}"
        else:
            # Seq num less than
            await self.disconnect(
                ConnectionState.DISCONNECTED_BROKEN_CONN,
                logout_message=(
                    "MsgSeqNum is too low, expected"
                    f" {self.session.next_num_in}, got {msg_seq_num}"
                ),
            )

    async def _process_message(self, decoded_msg: FIXMessage, raw_msg: bytes):
        self.log.debug(f"process_message (INCOMING)\n\t {decoded_msg}")
        if not self._validate_intergity(decoded_msg):
            # Some mandatory tags are missing or corrupt message
            await self.disconnect(ConnectionState.DISCONNECTED_BROKEN_CONN)
            return

        try:
            assert self.connection_state >= ConnectionState.NETWORK_CONN_ESTABLISHED

            self.message_last_time = time.time()

            if self.connection_state == ConnectionState.NETWORK_CONN_ESTABLISHED:
                # Applicable only for acceptor
                if decoded_msg.msg_type != FMsg.LOGON:
                    # According to FIX session spec, first message must be Logon()
                    #  we must drop connection without Logout() if first message was
                    #  not logon
                    await self.disconnect(ConnectionState.DISCONNECTED_BROKEN_CONN)
                    return
                self.connection_state = ConnectionState.LOGON_INITIAL_RECV
                self.connection_role = ConnectionRole.ACCEPTOR

            if decoded_msg.msg_type == FMsg.LOGON:
                await self._process_logon(decoded_msg)
            else:
                assert False, "Implement!"
                # if self.connection_state == ConnectionState.LOGGED_IN:
                #     await self.on_message(decoded_msg)
                # else:
                #     assert False, "Unexpected"
        except asyncio.CancelledError:
            raise
        except Exception:
            self.log.exception("_process_message error: ")
            raise
        finally:
            self.session.set_recv_seq_no(decoded_msg[FTag.MsgSeqNum])
            self.journaler.persist_msg(raw_msg, self.session, MessageDirection.INBOUND)

    async def send_msg(self, msg: FIXMessage):
        if self.connection_state < ConnectionState.NETWORK_CONN_ESTABLISHED:
            raise FIXConnectionError(
                "Connection must be established before sending any "
                f"FIX message, got state: {repr(self.connection_state)}"
            )
        elif self.connection_state == ConnectionState.NETWORK_CONN_ESTABLISHED:
            # INITIATOR mode, connection was just established
            if msg.msg_type != FMsg.LOGON:
                raise FIXConnectionError(
                    "You must send first Logon(35=A) message immediately after"
                    f" connection, got {repr(msg)}"
                )
            self.connection_state = ConnectionState.LOGON_INITIAL_SENT
            self.connection_role = ConnectionRole.INITIATOR
        else:
            if self.connection_role == ConnectionRole.INITIATOR:
                if (
                    self.connection_state == ConnectionState.LOGON_INITIAL_SENT
                    and msg.msg_type != FMsg.LOGOUT
                ):
                    raise FIXConnectionError(
                        "Initiator is waiting for Logon() response, you must not send"
                        " any additional messages before acceptor responce."
                    )

        encoded_msg = self.codec.encode(msg, self.session).encode("utf-8")

        msg_raw = encoded_msg.replace(b"\x01", b"|")
        self.log.debug(f"send_msg: (OUTBOUND)\n\t{msg_raw.decode()}")

        self.socket_writer.write(encoded_msg)
        await self.socket_writer.drain()

        self.journaler.persist_msg(encoded_msg, self.session, MessageDirection.OUTBOUND)
