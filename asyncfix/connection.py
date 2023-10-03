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

    RESENDREQ_HANDLING = 10            # both
    """Receive and respond to counterparty’s ResendRequest(35=2) sending requested
       messages and/or SequenceReset(35=4) gap fill messages for the range of
       MsgSeqNum(34) requested."""

    RECV_SEQNUM_TOO_HIGH = 11        # both
    """Receive too high of MsgSeqNum(34) from counterparty, queue message,
       and send ResendRequest(35=2)."""

    RESENDREQ_AWAITING = 12          # both
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
        self.connection_state = ConnectionState.DISCONNECTED_NOCONN_TODAY
        self.connection_was_active = False
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
        """
        Underlying FIXProtocolBase of a connection

        Returns:
        """
        return self.codec.protocol

    async def connect(self):
        """
        Transport initialization method

        Raises:
            NotImplementedError:

        """
        raise NotImplementedError("connect() is not implemented in child")

    async def disconnect(
        self,
        disconn_state: ConnectionState,
        logout_message: str = None,
    ):
        """
        Disconnect session and closes the socket

        Args:
            disconn_state: connection state after disconnection
            logout_message: if not None, sends Logout() message to peer with
                            (58=logout_message)
        """
        if self.connection_state > ConnectionState.DISCONNECTED_BROKEN_CONN:
            assert disconn_state <= ConnectionState.DISCONNECTED_BROKEN_CONN

            if logout_message is not None:
                msg = FIXMessage(FMsg.LOGOUT)
                if logout_message:
                    # Only add message if logout_message != ""
                    msg[FTag.Text] = logout_message
                await self.send_msg(msg)

            self.log.info(f"Client disconnected, with state: {repr(disconn_state)}")
            if self.socket_writer:
                self.socket_writer.close()
                await self.socket_writer.wait_closed()
            self.socket_writer = None
            self.socket_reader = None
            self._state_set(disconn_state)
            await self.on_disconnect()

    async def send_msg(self, msg: FIXMessage):
        """
        Sends message to the peer

        Args:
            msg: fix message

        Raises:
            FIXConnectionError: raised if connection state does not allow sending

        """
        if self.connection_state < ConnectionState.NETWORK_CONN_ESTABLISHED:
            raise FIXConnectionError(
                "Connection must be established before sending any "
                f"FIX message, got state: {repr(self.connection_state)}"
            )
        elif self.connection_state == ConnectionState.NETWORK_CONN_ESTABLISHED:
            # INITIATOR mode, connection was just established
            if msg.msg_type != FMsg.LOGON and msg.msg_type != FMsg.LOGOUT:
                raise FIXConnectionError(
                    "You must send first Logon(35=A)/Logout() message immediately after"
                    f" connection, got {repr(msg)}"
                )
            self._state_set(ConnectionState.LOGON_INITIAL_SENT)
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
        self.log.debug(
            f"send_msg: (OUTBOUND | {self.connection_role})"
            f" {repr(msg.msg_type)}\n\t{msg_raw.decode()}"
        )

        self.socket_writer.write(encoded_msg)
        await self.socket_writer.drain()

        self.journaler.persist_msg(encoded_msg, self.session, MessageDirection.OUTBOUND)

    async def socket_read_task(self):
        """
        Main socket reader task (decode raw messages and calls _process_message)
        """
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
                    if (
                        self.connection_state
                        <= ConnectionState.DISCONNECTED_BROKEN_CONN
                    ):
                        break

                    (decoded_msg, parsed_length, raw_msg) = self.codec.decode(
                        self.msg_buffer
                    )
                    # self.log.debug(decoded_msg)

                    if parsed_length > 0:
                        self.msg_buffer = self.msg_buffer[parsed_length:]

                    if decoded_msg is None:
                        break

                    await self._process_message(decoded_msg, raw_msg)
            except asyncio.CancelledError:
                raise
            except ConnectionError as why:
                self.log.debug("Connection has been closed %s" % (why,))
                await self.disconnect(ConnectionState.DISCONNECTED_BROKEN_CONN)
                continue
            except Exception:
                self.log.exception("handle_read exception")
                # raise

    async def heartbeat_timer_task(self):
        """
        Heartbeat watcher task
        """
        while True:
            try:
                if not self.socket_writer or not self.socket_reader:
                    # Socket was not connected, just wait
                    await asyncio.sleep(1)
                    continue

                if self.connection_state == ConnectionState.ACTIVE:
                    if time.time() - self.message_last_time > self.heartbeat_period - 1:
                        await self.send_msg(self.protocol.heartbeat())
                        self.message_last_time = time.time()

                if time.time() - self.message_last_time > self.heartbeat_period * 2:
                    # Dead socket probably
                    await self.disconnect(ConnectionState.DISCONNECTED_BROKEN_CONN)

            except asyncio.CancelledError:
                raise
            except Exception:
                self.log.exception("heartbeat_timer() error")
            await asyncio.sleep(1.0)

    async def reset_seq_num(self):
        # TODO: implement resetting session numbers with SequenceReset(GapFillFlag=N)
        pass

    ####################################################
    #
    #  User Application methods
    #
    ####################################################

    async def on_message(self, msg: FIXMessage):
        """
        (AppEvent) Business message was received

        Typically excludes session messages

        Args:
            msg:

        """
        pass

    async def on_connect(self):
        """
        (AppEvent) Underlying socket connected

        """
        pass

    async def on_disconnect(self):
        """
        (AppEvent) Underlying socket disconnected

        """
        pass

    async def on_logon(self, is_healthy: bool):
        """
        (AppEvent) Logon(35=A) received from peer

        Args:
            is_healthy: True - if connection_state is ACTIVE
        """
        pass

    async def on_logout(self):
        """
        (AppEvent) Logout(35=5) received from peer

        Args:
            msg:

        """
        pass

    def on_state_change(self, connection_state: ConnectionState):
        """
        (AppEvent) On ConnectionState change

        Args:
            connection_state: new connection state
        """
        pass

    def should_replay(self, historical_replay_msg: FIXMessage):
        """
        (AppLevel) Checks if historical_replay_msg from Journaler should be replayed

        Args:
            historical_replay_msg: message from Journaler log

        Returns: True - replay, False - msg skipped (replaced by SequenceReset(35=4))

        """
        return True

    ####################################################
    #
    #  Private methods
    #
    ####################################################

    def _state_set(self, connection_state: ConnectionState):
        """
        Sets internal connection state

        Args:
            connection_state:

        """
        self.connection_state = connection_state
        if connection_state == ConnectionState.ACTIVE:
            self.connection_was_active = True
        self.on_state_change(connection_state)

    def _validate_intergity(self, msg: FIXMessage) -> bool:
        """
        Validates incoming message critical integrity

        Args:
            msg: incoming message

        Returns:
            None - if no error
            True - if critical error (no Logout() message has to be sent)
            "err msg" - Logout(58="err msg") should be sent
        """
        if msg[FTag.BeginString] != self.protocol.beginstring:
            return (
                "Protocol BeginString(8) mismatch, expected"
                f" {self.protocol.beginstring}, got {msg[FTag.BeginString]}"
            )
        if FTag.SenderCompID not in msg or FTag.TargetCompID not in msg:
            # this will drop connection without a message
            return True

        if not self.session.validate_comp_ids(
            msg[FTag.SenderCompID], msg[FTag.TargetCompID]
        ):
            # Sender/Target are reversed here
            return "TargetCompID / SenderCompID mismatch"

        # TODO: validate SendingTime ~~ within 2x heartbeat_period
        if FTag.MsgSeqNum not in msg:
            return "MsgSeqNum(34) tag is missing"

        msg_seq_num = int(msg[FTag.MsgSeqNum])
        if msg_seq_num < self.session.next_num_in:
            return (
                f"MsgSeqNum is too low, expected {self.session.next_num_in}, got"
                f" {msg_seq_num}"
            )

        # All good
        return None

    async def _process_logon(self, logon_msg: FIXMessage):
        """
        Processes Logon(35=A) message
        """
        assert logon_msg.msg_type == FMsg.LOGON
        assert (
            self.connection_role == ConnectionRole.ACCEPTOR
            or self.connection_role == ConnectionRole.INITIATOR
        )

        msg_seq_num = int(logon_msg[FTag.MsgSeqNum])

        if self.connection_role == ConnectionRole.ACCEPTOR:
            assert self.connection_state == ConnectionState.LOGON_INITIAL_RECV
            if msg_seq_num >= self.session.next_num_in:
                msg_logon = FIXMessage(FMsg.LOGON)
                msg_logon.set(FTag.EncryptMethod, logon_msg[FTag.EncryptMethod])
                msg_logon.set(FTag.HeartBtInt, logon_msg[FTag.HeartBtInt])
                await self.send_msg(msg_logon)

        if msg_seq_num == self.session.next_num_in:
            self._state_set(ConnectionState.ACTIVE)
            # TODO: decide send extra test request?
        else:
            self._state_set(ConnectionState.RECV_SEQNUM_TOO_HIGH)

        await self.on_logon(self.connection_state == ConnectionState.ACTIVE)

    async def _check_seqnum_gaps(self, msg_seq_num: int) -> bool:
        """
        Validates incoming MsgSeqNum, sends ResendRequest(35=2) if gap

        Args:
            msg_seq_num:

        Returns:
            True - no gap, MsgSeqNum is correct
            False - there is a gap, ResendRequest() sent
        """
        if (
            msg_seq_num > self.session.next_num_in
            and self.connection_state != ConnectionState.RESENDREQ_AWAITING
        ):
            resend_req = FIXMessage(
                FMsg.RESENDREQUEST,
                {FTag.BeginSeqNo: self.session.next_num_in, FTag.EndSeqNo: "0"},
            )
            await self.send_msg(resend_req)
            self._state_set(ConnectionState.RESENDREQ_AWAITING)
            return False

        return True

    async def _process_logout(self, logout_msg: FIXMessage):
        """
        Processes incoming Logout(35=5) message

        Args:
            msg: Logout(35=5) FIXMessage
        """
        assert logout_msg.msg_type == FMsg.LOGOUT

        if self.connection_was_active:
            dstate = ConnectionState.DISCONNECTED_WCONN_TODAY
        else:
            dstate = ConnectionState.DISCONNECTED_BROKEN_CONN

        await self.disconnect(dstate)

    async def _process_resend(self, resend_msg: FIXMessage):
        """
        Handles ResendRequest(35=2) - fills message gaps

        Args:
            msg: ResendRequest(35=2) FIXMessage

        """
        assert resend_msg.msg_type == FMsg.RESENDREQUEST
        assert self.connection_state == ConnectionState.RESENDREQ_HANDLING

        begin_seq_no = resend_msg[FTag.BeginSeqNo]
        end_seq_no = resend_msg[FTag.EndSeqNo]
        if int(end_seq_no) == 0:
            end_seq_no = sys.maxsize
        self.log.info("Received resent request from %s to %s", begin_seq_no, end_seq_no)
        journal_replay_msgs = self.journaler.recover_messages(
            self.session, MessageDirection.OUTBOUND, begin_seq_no, end_seq_no
        )
        gap_fill_begin = int(begin_seq_no)
        gap_fill_end = int(begin_seq_no)

        noreply_msgs = {
            FMsg.LOGON,
            FMsg.LOGOUT,
            FMsg.RESENDREQUEST,
            FMsg.HEARTBEAT,
            FMsg.TESTREQUEST,
            FMsg.SEQUENCERESET,
        }

        for enc_msg in journal_replay_msgs:
            replay_msg, _, _ = self.codec.decode(enc_msg, silent=False)
            msg_seq_num = int(replay_msg[FTag.MsgSeqNum])

            is_sess_msg = replay_msg[FTag.MsgType] in noreply_msgs
            if is_sess_msg or not self.should_replay(replay_msg):
                gap_fill_end = msg_seq_num + 1
            else:
                if gap_fill_begin < gap_fill_end:
                    # we need to send a gap fill message
                    gap_fill_msg = FIXMessage(FMsg.SEQUENCERESET)
                    gap_fill_msg[FTag.GapFillFlag] = "Y"
                    gap_fill_msg[FTag.MsgSeqNum] = gap_fill_begin
                    gap_fill_msg[FTag.NewSeqNo] = str(gap_fill_end)
                    # breakpoint()
                    await self.send_msg(gap_fill_msg)

                # and then resent the replayMsg
                replay_msg[FTag.PossDupFlag] = "Y"
                replay_msg[FTag.OrigSendingTime] = replay_msg[FTag.SendingTime]
                del replay_msg[FTag.MsgType]
                del replay_msg[FTag.BeginString]
                del replay_msg[FTag.BodyLength]
                del replay_msg[FTag.SendingTime]
                del replay_msg[FTag.SenderCompID]
                del replay_msg[FTag.TargetCompID]
                del replay_msg[FTag.CheckSum]
                await self.send_msg(replay_msg)

                gap_fill_begin = msg_seq_num + 1

        if gap_fill_end < gap_fill_begin:
            self.log.warning(
                f"Journal MsgSeqNum not reflecting last {self.session.next_num_out=},"
                " forcing reset."
            )

        assert gap_fill_end <= self.session.next_num_out, "Unexpected end for gap"

        # Remainder not available in some reason
        if gap_fill_begin < self.session.next_num_out:
            gap_fill_msg = FIXMessage(FMsg.SEQUENCERESET)
            gap_fill_msg[FTag.GapFillFlag] = "Y"
            gap_fill_msg[FTag.MsgSeqNum] = gap_fill_begin
            gap_fill_msg[FTag.NewSeqNo] = str(self.session.next_num_out + 1)
            await self.send_msg(gap_fill_msg)

        if self.connection_state != ConnectionState.RESENDREQ_AWAITING:
            self._state_set(ConnectionState.ACTIVE)

    async def _process_seqreset(self, seqreset_msg: FIXMessage):
        assert seqreset_msg.msg_type == FMsg.SEQUENCERESET

        if seqreset_msg.get(FTag.GapFillFlag, None) == "Y":
            if self.connection_state != ConnectionState.RESENDREQ_AWAITING:
                self.log.warning(
                    "Getting SEQUENCERESET(GapFillFlag=Y) while not filling gaps"
                )
        else:
            self.log.info(f"SequenceReset received from peer: {seqreset_msg}")

    async def _finalize_message(self, msg: FIXMessage, raw_msg: bytes):
        msg_sec_no = self.session.set_next_num_in(msg)
        if msg_sec_no == 0:
            self.log.warning(f"Got possible garbled message: {msg}")
            # Garbled message without needed tags
            return
        elif msg_sec_no == -1:
            # TODO: decide probably need to que message
            return

        if (
            self.connection_state == ConnectionState.RESENDREQ_AWAITING
            and msg_sec_no == self.session.next_num_in - 1
        ):
            # All messages were transferred
            # breakpoint()
            self._state_set(ConnectionState.ACTIVE)
            pass

        self.journaler.persist_msg(raw_msg, self.session, MessageDirection.INBOUND)

    async def _process_message(self, msg: FIXMessage, raw_msg: bytes):
        """
        Main message processing dispatcher

        Args:
            msg: incoming decoded message
            raw_msg: incoming raw message (bytes)

        """
        self.log.debug(
            f"process_message (INCOMING | {self.connection_role})"
            f" {repr(msg.msg_type)}\n\t {msg}"
        )
        err_msg = self._validate_intergity(msg)
        if err_msg:
            # Some mandatory tags are missing or corrupt message
            await self.disconnect(
                ConnectionState.DISCONNECTED_BROKEN_CONN,
                logout_message=err_msg if isinstance(err_msg, str) else None,
            )
            return

        try:
            assert self.connection_state >= ConnectionState.NETWORK_CONN_ESTABLISHED

            self.message_last_time = time.time()

            if self.connection_state == ConnectionState.NETWORK_CONN_ESTABLISHED:
                # Applicable only for acceptor
                if msg.msg_type != FMsg.LOGON:
                    # According to FIX session spec, first message must be Logon()
                    #  we must drop connection without Logout() if first message was
                    #  not logon
                    await self.disconnect(ConnectionState.DISCONNECTED_BROKEN_CONN)
                    return
                self._state_set(ConnectionState.LOGON_INITIAL_RECV)
                self.connection_role = ConnectionRole.ACCEPTOR

            if msg.msg_type == FMsg.LOGON:
                await self._process_logon(msg)

            msg_seq_num = int(msg[FTag.MsgSeqNum])
            await self._check_seqnum_gaps(msg_seq_num)

            if msg.msg_type == FMsg.RESENDREQUEST:
                self._state_set(ConnectionState.RESENDREQ_HANDLING)
                await self._process_resend(msg)
            elif msg.msg_type == FMsg.SEQUENCERESET:
                await self._process_seqreset(msg)
            elif msg.msg_type == FMsg.LOGON:
                pass  # already processed
            elif msg.msg_type == FMsg.LOGOUT:
                await self._process_logout(msg)
            else:
                assert False, "Stub!"
                await self.on_message(msg)

        except asyncio.CancelledError:
            raise
        except Exception:
            self.log.exception("_process_message error: ")
            raise
        finally:
            await self._finalize_message(msg, raw_msg)
