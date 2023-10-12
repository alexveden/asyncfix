import asyncio
import logging
import sys
import time
from enum import Enum, IntEnum

from asyncfix import FMsg, FTag
from asyncfix.codec import Codec
from asyncfix.errors import FIXConnectionError
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
    """
    AsyncFIX bidirectional connection

    Attributes:
        connection_state: Current connection_state
        connection_role: Current connection_role ACCEPTOR | INITIATOR
        log: logger

    """

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
    ):
        """
        AsyncFIX bidirectional connection

        Args:
            protocol: FIX protocol
            sender_comp_id: initiator SenderCompID
            target_comp_id: acceptor TargetCompID
            journaler: fix messages journaling engine
            host: endpoint host
            port: endpoint port
            heartbeat_period: heartbeat interval in seconds
            logger: logger instance (by default logging.getLogger())
            start_tasks: True - starts socket/heartbeat asyncio tasks, False - no tasks
                        (this is useful in debugging / testing)
        """
        if not logger:
            self.log: logging.Logger = logging.getLogger()
        else:
            self.log: logging.Logger = logger

        # Private attributes
        self._connection_state: ConnectionState = (
            ConnectionState.DISCONNECTED_NOCONN_TODAY
        )
        self._connection_role: ConnectionRole = ConnectionRole.UNKNOWN
        self._codec = Codec(protocol)
        self._journaler: Journaler = journaler
        self._session: FIXSession = journaler.create_or_load(
            target_comp_id, sender_comp_id
        )
        self._connection_was_active = False
        self._msg_buffer = b""
        self._heartbeat_period = heartbeat_period
        self._message_last_time = 0.0
        self._max_seq_num_resend = 0
        self._test_req_id = None
        self._socket_reader: asyncio.StreamReader = None
        self._socket_writer: asyncio.StreamWriter = None
        self._host = host
        self._port = int(port)
        self._aio_task_socket_read = None
        self._aio_task_heartbeat = None

    @property
    def connection_state(self) -> ConnectionState:
        return self._connection_state

    @property
    def connection_role(self) -> ConnectionRole:
        return self._connection_role

    @property
    def heartbeat_period(self) -> int:
        return self._heartbeat_period

    @property
    def protocol(self) -> FIXProtocolBase:
        """
        Underlying FIXProtocolBase of a connection

        Returns:
        """
        return self._codec.protocol

    async def connect(self):
        """
        Transport initialization method

        Raises:
            NotImplementedError:

        """
        if not self._aio_task_socket_read:
            self._aio_task_socket_read = asyncio.create_task(self.socket_read_task())
        if not self._aio_task_heartbeat:
            self._aio_task_heartbeat = asyncio.create_task(self.heartbeat_timer_task())

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
        if self._connection_state > ConnectionState.DISCONNECTED_BROKEN_CONN:
            assert disconn_state <= ConnectionState.DISCONNECTED_BROKEN_CONN
            self._test_req_id = None
            self._message_last_time = 0.0
            self._max_seq_num_resend = 0

            if logout_message is not None:
                msg = FIXMessage(FMsg.LOGOUT)
                if logout_message:
                    # Only add message if logout_message != ""
                    msg[FTag.Text] = logout_message
                await self.send_msg(msg)

            self.log.info(f"Client disconnected, with state: {repr(disconn_state)}")
            if self._socket_writer:
                self._socket_writer.close()
                await self._socket_writer.wait_closed()
            self._socket_writer = None
            self._socket_reader = None
            await self._state_set(disconn_state)
            await self.on_disconnect()

    async def send_msg(self, msg: FIXMessage):
        """
        Sends message to the peer

        Args:
            msg: fix message

        Raises:
            FIXConnectionError: raised if connection state does not allow sending

        """
        if self._connection_state < ConnectionState.NETWORK_CONN_ESTABLISHED:
            raise FIXConnectionError(
                "Connection must be established before sending any "
                f"FIX message, got state: {repr(self._connection_state)}"
            )
        elif self._connection_state == ConnectionState.NETWORK_CONN_ESTABLISHED:
            # INITIATOR mode, connection was just established
            if msg.msg_type != FMsg.LOGON and msg.msg_type != FMsg.LOGOUT:
                raise FIXConnectionError(
                    "You must send first Logon(35=A)/Logout() message immediately after"
                    f" connection, got {repr(msg)}"
                )
            await self._state_set(ConnectionState.LOGON_INITIAL_SENT)
            self._connection_role = ConnectionRole.INITIATOR
        else:
            if self._connection_role == ConnectionRole.INITIATOR:
                if (
                    self._connection_state == ConnectionState.LOGON_INITIAL_SENT
                    and msg.msg_type != FMsg.LOGOUT
                ):
                    raise FIXConnectionError(
                        "Initiator is waiting for Logon() response, you must not send"
                        " any additional messages before acceptor responce."
                    )

        if msg.msg_type == FMsg.TESTREQUEST and self._test_req_id is None:
            raise FIXConnectionError(
                "You must rend TestRequest() message via self.send_test_req() method in"
                " order to get valid response handling"
            )

        encoded_msg = self._codec.encode(msg, self._session).encode("utf-8")

        msg_raw = encoded_msg.replace(b"\x01", b"|")
        self.log.debug(
            f"[{self._connection_role.name}]:send_msg ({self._connection_state.name})"
            f" {repr(msg.msg_type)}\n\t {msg_raw.decode()}\n"
        )

        self._socket_writer.write(encoded_msg)
        await self._socket_writer.drain()

        self._journaler.persist_msg(
            encoded_msg, self._session, MessageDirection.OUTBOUND
        )

    async def send_test_req(self):
        """
        Sends TestRequest(35=1) and sets TestReqID for expected response from peer

        Raises:
            FIXConnectionError: if another TestRequest() is pending

        """
        if self._test_req_id is not None:
            raise FIXConnectionError("Another test request already pending")

        self._test_req_id = int(time.time())
        test_msg = FIXMessage(FMsg.TESTREQUEST, {FTag.TestReqID: self._test_req_id})
        await self.send_msg(test_msg)

    async def socket_read_task(self):
        """
        Main socket reader task (decode raw messages and calls _process_message)
        """
        last_connect = time.time()

        while True:
            try:
                if not self._socket_reader:
                    # Socket was not connected, just wait
                    await asyncio.sleep(1)
                    if self.connection_role == ConnectionRole.INITIATOR:
                        if time.time() - last_connect > self.heartbeat_period * 1.5:
                            self.log.debug("Trying reconnect")
                            last_connect = time.time()
                            await self.connect()
                    continue

                msg = await self._socket_reader.read(4096)
                if not msg:
                    raise ConnectionError

                self._msg_buffer = self._msg_buffer + msg
                while True:
                    if (
                        self._connection_state
                        <= ConnectionState.DISCONNECTED_BROKEN_CONN
                    ):
                        break

                    (decoded_msg, parsed_length, raw_msg) = self._codec.decode(
                        self._msg_buffer
                    )
                    # self.log.debug(decoded_msg)

                    if parsed_length > 0:
                        self._msg_buffer = self._msg_buffer[parsed_length:]

                    if decoded_msg is None:
                        break

                    await self._process_message(decoded_msg, raw_msg)
            except asyncio.CancelledError:
                return
            except ConnectionError as why:
                self.log.debug(
                    "socket_read_task: connection has been closed %s" % (why,)
                )
                await self.disconnect(ConnectionState.DISCONNECTED_BROKEN_CONN)

                # Reset reconnect time
                last_connect = time.time()
                continue
            except Exception:
                self.log.exception("socket_read_task: exception")
                # raise

    async def heartbeat_timer_task(self):
        """
        Heartbeat watcher task
        """
        while True:
            try:
                if not self._socket_writer or not self._socket_reader:
                    # Socket was not connected, just wait
                    await asyncio.sleep(1)
                    continue

                tm = time.time()

                if self._connection_state == ConnectionState.ACTIVE:
                    if tm - self._message_last_time > self._heartbeat_period - 1:
                        if not self._test_req_id:
                            await self.send_test_req()
                        self._message_last_time = tm

                if (
                    self._message_last_time
                    and tm - self._message_last_time > self._heartbeat_period * 2
                ):
                    # Dead socket probably
                    self.log.debug("heartbeat_timer_task: message last time timeout")
                    await self.disconnect(ConnectionState.DISCONNECTED_BROKEN_CONN)

                if (
                    self._test_req_id
                    and tm - self._test_req_id > self._heartbeat_period * 2
                ):
                    # No sensible reply on TestRequest
                    self.log.debug("heartbeat_timer_task: test request timeout")
                    await self.disconnect(ConnectionState.DISCONNECTED_BROKEN_CONN)

                await asyncio.sleep(1.0)
            except asyncio.CancelledError:
                return
            except Exception:
                self.log.exception("heartbeat_timer() error")

    async def reset_seq_num(self):
        self.log.info("Resetting connection sequence and journal")
        self._journaler.set_seq_num(self._session, next_num_in=1, next_num_out=1)
        assert self._session.next_num_in == 1
        assert self._session.next_num_out == 1

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
        raise NotImplementedError("on_message() must be implemented in app class")

    async def on_connect(self):
        """
        (AppEvent) Underlying socket connected

        """
        raise NotImplementedError("on_connect() must be implemented in app class")
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

    async def on_logout(self, msg: FIXMessage):
        """
        (AppEvent) Logout(35=5) received from peer

        Args:
            msg:

        """
        pass

    async def on_state_change(self, connection_state: ConnectionState):
        """
        (AppEvent) On ConnectionState change

        Args:
            connection_state: new connection state
        """
        pass

    async def should_replay(self, historical_replay_msg: FIXMessage) -> bool:
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

    async def _state_set(self, connection_state: ConnectionState):
        """
        Sets internal connection state

        Args:
            connection_state:

        """
        self.log.debug(
            f"[{self._connection_role.name}] NewState: {connection_state.name}"
        )
        self._connection_state = connection_state
        if connection_state == ConnectionState.ACTIVE:
            self._connection_was_active = True
        await self.on_state_change(connection_state)

    def _validate_integrity(self, msg: FIXMessage) -> bool:
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

        if not self._session.validate_comp_ids(
            msg[FTag.SenderCompID], msg[FTag.TargetCompID]
        ):
            # Sender/Target are reversed here
            return "TargetCompID / SenderCompID mismatch"

        # TODO: validate SendingTime ~~ within 2x heartbeat_period
        if FTag.MsgSeqNum not in msg:
            return "MsgSeqNum(34) tag is missing"

        msg_seq_num = int(msg[FTag.MsgSeqNum])
        if msg_seq_num < self._session.next_num_in:
            _is_err = True
            if msg.msg_type == FMsg.SEQUENCERESET:
                _is_err = False
            if self._connection_state == ConnectionState.RESENDREQ_AWAITING:
                _is_err = False

            if _is_err:
                return (
                    f"MsgSeqNum is too low, expected {self._session.next_num_in}, got"
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
            self._connection_role == ConnectionRole.ACCEPTOR
            or self._connection_role == ConnectionRole.INITIATOR
        )

        msg_seq_num = int(logon_msg[FTag.MsgSeqNum])

        if self._connection_role == ConnectionRole.ACCEPTOR:
            assert self._connection_state == ConnectionState.LOGON_INITIAL_RECV
            if msg_seq_num >= self._session.next_num_in:
                msg_logon = FIXMessage(FMsg.LOGON)
                msg_logon.set(FTag.EncryptMethod, logon_msg[FTag.EncryptMethod])
                msg_logon.set(FTag.HeartBtInt, logon_msg[FTag.HeartBtInt])
                await self.send_msg(msg_logon)

        if msg_seq_num == self._session.next_num_in:
            await self._state_set(ConnectionState.ACTIVE)
        else:
            await self._state_set(ConnectionState.RECV_SEQNUM_TOO_HIGH)

        await self.on_logon(self._connection_state == ConnectionState.ACTIVE)

    async def _check_seqnum_gaps(self, msg_seq_num: int) -> bool:
        """
        Validates incoming MsgSeqNum, sends ResendRequest(35=2) if gap

        Args:
            msg_seq_num:

        Returns:
            True - no gap, MsgSeqNum is correct
            False - there is a gap, ResendRequest() sent
        """
        if msg_seq_num > self._session.next_num_in:
            if self._connection_state != ConnectionState.RESENDREQ_AWAITING:
                resend_req = FIXMessage(
                    FMsg.RESENDREQUEST,
                    {FTag.BeginSeqNo: self._session.next_num_in, FTag.EndSeqNo: "0"},
                )
                self._max_seq_num_resend = msg_seq_num
                await self.send_msg(resend_req)
                await self._state_set(ConnectionState.RESENDREQ_AWAITING)
            return False

        return True

    async def _process_logout(self, logout_msg: FIXMessage):
        """
        Processes incoming Logout(35=5) message

        Args:
            msg: Logout(35=5) FIXMessage
        """
        assert logout_msg.msg_type == FMsg.LOGOUT

        if self._connection_was_active:
            dstate = ConnectionState.DISCONNECTED_WCONN_TODAY
        else:
            dstate = ConnectionState.DISCONNECTED_BROKEN_CONN

        await self.on_logout(logout_msg)

        await self.disconnect(dstate)

    async def _process_resend(self, resend_msg: FIXMessage):
        """
        Handles ResendRequest(35=2) - fills message gaps

        Args:
            msg: ResendRequest(35=2) FIXMessage

        """
        if self._connection_state != ConnectionState.RESENDREQ_AWAITING:
            await self._state_set(ConnectionState.RESENDREQ_HANDLING)

        assert resend_msg.msg_type == FMsg.RESENDREQUEST
        assert self._connection_state in {
            ConnectionState.RESENDREQ_HANDLING,
            ConnectionState.RESENDREQ_AWAITING,
        }

        begin_seq_no = int(resend_msg[FTag.BeginSeqNo])
        end_seq_no = int(resend_msg[FTag.EndSeqNo])
        if end_seq_no == 0:
            end_seq_no = sys.maxsize
        self.log.info("Received resent request from %s to %s", begin_seq_no, end_seq_no)
        journal_replay_msgs = self._journaler.recover_messages(
            self._session, MessageDirection.OUTBOUND, begin_seq_no, end_seq_no
        )

        # Remember next_num_out
        current_next_num_out = self._session.next_num_out

        self._journaler.set_seq_num(self._session, next_num_out=begin_seq_no)
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
            replay_msg, _, _ = self._codec.decode(enc_msg, silent=False)
            msg_seq_num = int(replay_msg[FTag.MsgSeqNum])

            is_sess_msg = replay_msg[FTag.MsgType] in noreply_msgs
            if is_sess_msg or not await self.should_replay(replay_msg):
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
                "Journal MsgSeqNum not reflecting last"
                f" next_num_out={current_next_num_out}, forcing reset."
            )

        assert gap_fill_end <= current_next_num_out, "Unexpected end for gap"

        # Remainder not available in some reason
        if gap_fill_begin < current_next_num_out:
            gap_fill_msg = FIXMessage(FMsg.SEQUENCERESET)
            gap_fill_msg[FTag.GapFillFlag] = "Y"
            gap_fill_msg[FTag.MsgSeqNum] = gap_fill_begin
            gap_fill_msg[FTag.NewSeqNo] = current_next_num_out
            await self.send_msg(gap_fill_msg)

        self._journaler.set_seq_num(self._session, next_num_out=current_next_num_out)

        if self._connection_state != ConnectionState.RESENDREQ_AWAITING:
            await self._state_set(ConnectionState.ACTIVE)

    async def _process_seqreset(self, seqreset_msg: FIXMessage):
        """
        Handles SequenceReset(35=4) message

        Args:
            seqreset_msg:

        """
        assert seqreset_msg.msg_type == FMsg.SEQUENCERESET

        if seqreset_msg.get(FTag.GapFillFlag, None) == "Y":
            if self._connection_state != ConnectionState.RESENDREQ_AWAITING:
                self.log.warning(
                    "Getting SEQUENCERESET(GapFillFlag=Y) while not filling gaps"
                )
        else:
            self.log.info(f"SequenceReset received from peer: {seqreset_msg}")

        # Cleanup journal of past messages if session was reset to avoid SQL dup errors
        #   Sometimes we might have outdated seq nums in journal
        self._journaler.set_seq_num(
            self._session, next_num_in=int(seqreset_msg[FTag.MsgSeqNum])
        )

        # Set journal at new NewSeqNo
        self._journaler.set_seq_num(
            self._session, next_num_in=int(seqreset_msg[FTag.NewSeqNo])
        )

    async def _finalize_message(self, msg: FIXMessage, raw_msg: bytes):
        """
        Final message processing (MsgSeqNum checks / journaling)

        Args:
            msg: incoming message
            raw_msg: encoded message for journal
        """
        msg_sec_no = self._session.set_next_num_in(msg)

        if msg_sec_no <= 0:
            self.log.warning(f"Trying to finalize invalid {msg=}")
            return

        if self._connection_state == ConnectionState.RESENDREQ_AWAITING:
            assert self._max_seq_num_resend > 0

            if msg_sec_no >= self._max_seq_num_resend:
                # All messages were transferred
                self._max_seq_num_resend = 0
                await self._state_set(ConnectionState.ACTIVE)

        self._message_last_time = time.time()

        self._journaler.persist_msg(raw_msg, self._session, MessageDirection.INBOUND)

    async def _process_testrequest(self, testreq_msg: FIXMessage):
        """
        Handles TestRequest(35=1)

        Replies with Heartbeat(35=0) message with TestReqID tag

        Args:
            testreq_msg: TestRequest FIXMessage

        """
        assert testreq_msg.msg_type == FMsg.TESTREQUEST
        hbt_msg = FIXMessage(
            FMsg.HEARTBEAT, {FTag.TestReqID: testreq_msg.get(FTag.TestReqID, 0)}
        )
        await self.send_msg(hbt_msg)

    async def _process_heartbeat(self, hbt_msg: FIXMessage):
        """
        Handles Heartbeat(35=0) message (possible response on TestRequest(35=1))

        Args:
            hbt_msg: Heartbeat(35=0) FIXMessage

        """
        assert hbt_msg.msg_type == FMsg.HEARTBEAT

        if self._test_req_id is not None:
            if FTag.TestReqID not in hbt_msg:
                # Possibly interval Heartbeat, just skip
                return

            # Expecting test_req_id
            try:
                msg_test_id = int(hbt_msg.get(FTag.TestReqID, "0"))
            except Exception:
                msg_test_id = 0

            if self._test_req_id != msg_test_id:
                await self.disconnect(
                    ConnectionState.DISCONNECTED_BROKEN_CONN,
                    logout_message="Invalid TestRequest(TestReqID) received",
                )
            else:
                self._test_req_id = None

    async def _process_message(self, msg: FIXMessage, raw_msg: bytes):
        """
        Main message processing dispatcher

        Args:
            msg: incoming decoded message
            raw_msg: incoming raw message (bytes)

        """
        self.log.debug(
            f"[{self._connection_role.name}]:process_message"
            f" ({self._connection_state.name}) {repr(msg.msg_type)}\n\t {msg}\n"
        )

        err_msg = self._validate_integrity(msg)
        if err_msg:
            # Some mandatory tags are missing or corrupt message
            await self.disconnect(
                ConnectionState.DISCONNECTED_BROKEN_CONN,
                logout_message=err_msg if isinstance(err_msg, str) else None,
            )
            return
        is_valid_msg_num = False
        try:
            assert self._connection_state >= ConnectionState.NETWORK_CONN_ESTABLISHED

            if self._connection_state == ConnectionState.NETWORK_CONN_ESTABLISHED:
                # Applicable only for acceptor
                if msg.msg_type != FMsg.LOGON:
                    # According to FIX session spec, first message must be Logon()
                    #  we must drop connection without Logout() if first message was
                    #  not logon
                    await self.disconnect(ConnectionState.DISCONNECTED_BROKEN_CONN)
                    return
                await self._state_set(ConnectionState.LOGON_INITIAL_RECV)
                self._connection_role = ConnectionRole.ACCEPTOR

            if msg.msg_type == FMsg.LOGON:
                await self._process_logon(msg)
            elif msg.msg_type == FMsg.SEQUENCERESET:
                await self._process_seqreset(msg)
            elif msg.msg_type == FMsg.LOGOUT:
                await self._process_logout(msg)

            if self._connection_state <= ConnectionState.DISCONNECTED_BROKEN_CONN:
                # Got logout probably
                return

            msg_seq_num = int(msg[FTag.MsgSeqNum])
            is_valid_msg_num = await self._check_seqnum_gaps(msg_seq_num)

            if msg.msg_type == FMsg.RESENDREQUEST:
                await self._process_resend(msg)
            elif msg.msg_type == FMsg.SEQUENCERESET:
                pass
            elif msg.msg_type == FMsg.LOGON:
                pass  # already processed
            elif msg.msg_type == FMsg.TESTREQUEST:
                await self._process_testrequest(msg)
            elif msg.msg_type == FMsg.HEARTBEAT:
                await self._process_heartbeat(msg)
            else:
                if is_valid_msg_num:
                    await self.on_message(msg)
                else:
                    self.log.debug(f"_process_message: skipped app msg: {msg}")

        except asyncio.CancelledError:
            raise
        except Exception:
            self.log.exception(
                f"[{self._connection_role.name}]:process_message"
                f" ({self._connection_state.name}) {repr(msg.msg_type)}\n\t {msg}\n"
            )
        finally:
            if is_valid_msg_num:
                await self._finalize_message(msg, raw_msg)
