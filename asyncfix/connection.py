import asyncio
import sys
import time
from enum import Enum
import logging
from asyncfix import FTag, FMsg
from asyncfix.errors import FIXConnectionError
from asyncfix.codec import Codec
from asyncfix.journaler import Journaler
from asyncfix.message import FIXMessage, MessageDirection
from asyncfix.protocol import FIXProtocolBase
from asyncfix.session import FIXSession


class ConnectionState(Enum):
    UNKNOWN = 0
    DISCONNECTED = 1
    CONNECTED = 2
    LOGGED_IN = 3
    LOGGED_OUT = 4


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
        self.connection_state = ConnectionState.DISCONNECTED
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

    async def disconnect(self):
        if self.connection_state != ConnectionState.DISCONNECTED:
            self.log.info("Client disconnected")
            if self.socket_writer:
                self.socket_writer.close()
            self.socket_writer = None
            self.socket_reader = None
            self.connection_state = ConnectionState.DISCONNECTED
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

    async def _handle_resend_request(self, msg: FIXMessage):
        begin_seq_no = msg[FTag.BeginSeqNo]
        end_seq_no = msg[FTag.EndSeqNo]
        if int(end_seq_no) == 0:
            end_seq_no = sys.maxsize
        logging.info("Received resent request from %s to %s", begin_seq_no, end_seq_no)
        replay_msgs = self.engine.journaller.recover_msgs(
            self.session, MessageDirection.OUTBOUND, begin_seq_no, end_seq_no
        )
        gap_fill_begin = int(begin_seq_no)
        gap_fill_end = int(begin_seq_no)
        for replay_msg in replay_msgs:
            msg_seq_num = int(replay_msg[FTag.MsgSeqNum])
            if replay_msg[FTag.MsgType] in self.codec.protocol.session_message_types:
                gap_fill_end = msg_seq_num + 1
            else:
                if self.engine.should_resend_message(self.session, replay_msg):
                    if gap_fill_begin < gap_fill_end:
                        # we need to send a gap fill message
                        gap_fill_msg = FIXMessage(FMsg.SEQUENCERESET)
                        gap_fill_msg[FTag.GapFillFlag] = "Y"
                        gap_fill_msg[FTag.MsgSeqNum] = gap_fill_begin
                        gap_fill_msg[FTag.NewSeqNo] = str(gap_fill_end)
                        await self.send_msg(gap_fill_msg)

                    # and then resent the replayMsg
                    del replay_msg[FTag.BeginString]
                    del replay_msg[FTag.BodyLength]
                    del replay_msg[FTag.SendingTime]
                    del replay_msg[FTag.SenderCompID]
                    del replay_msg[FTag.TargetCompID]
                    del replay_msg[FTag.CheckSum]
                    replay_msg[FTag.PossDupFlag] = "Y"
                    await self.send_msg(replay_msg)

                    gap_fill_begin = msg_seq_num + 1
                else:
                    gap_fill_end = msg_seq_num + 1
                    await self.send_msg(replay_msg)

        if gap_fill_begin < gap_fill_end:
            # we need to send a gap fill message
            gap_fill_msg = FIXMessage(FMsg.SEQUENCERESET)
            gap_fill_msg[FTag.GapFillFlag] = "Y"
            gap_fill_msg[FTag.MsgSeqNum] = gap_fill_begin
            gap_fill_msg[FTag.NewSeqNo] = str(gap_fill_end)
            await self.send_msg(gap_fill_msg)

    async def on_session_message(self, msg: FIXMessage):
        recv_seq_no = msg[FTag.MsgSeqNum]

        msg_type = msg[FTag.MsgType]
        target_comp_d = msg[FTag.TargetCompID]
        sender_comp_id = msg[FTag.SenderCompID]

        if msg_type == FMsg.LOGON:
            if self.connection_state == ConnectionState.LOGGED_IN:
                self.log.warning(
                    "Client session already logged in - ignoring login request"
                )
            else:
                self.connection_state = ConnectionState.LOGGED_IN
                self.heartbeat_period = float(msg[FTag.HeartBtInt])

            if not await self._validate_seqnums(msg):
                self.log.warning('unexpected seq nums')

        elif self.connection_state == ConnectionState.LOGGED_IN:
            self.message_last_time = time.time()
            # compids are reversed here
            if not self.session.validate_comp_ids(sender_comp_id, target_comp_d):
                self.log.error("Received message with unexpected comp ids")
                await self.disconnect()
                return False

            if msg_type == FMsg.LOGOUT:
                self.connection_state = ConnectionState.LOGGED_OUT
                await self.disconnect()
            elif msg_type == FMsg.TESTREQUEST:
                # https://www.fixtrading.org/standards/fix-session-layer-online/#message-exchange-during-a-fix-connection # noqa
                #    see "Test request processing" section
                #  required to reply with TestReqID from query
                hbt_msg = self.protocol.heartbeat()
                hbt_msg[FTag.TestReqID] = msg[FTag.TestReqID]
                await self.send_msg(hbt_msg)
            elif msg_type == FMsg.RESENDREQUEST:
                self.log.info("on_session_message: Resend request")
                reset_msg = self.protocol.sequence_reset(
                    self.session.snd_seq_num + 2,
                    is_gap_fill=False,
                )
                # reset_msg[FTag.MsgSeqNum] = self.session.snd_seq_num
                await self.send_msg(reset_msg)
            elif msg_type == FMsg.SEQUENCERESET:
                self.log.info("on_session_message: SequenceReset request")

                new_seq_no = msg[FTag.NewSeqNo]
                if msg.get(FTag.GapFillFlag, "N") == "Y":
                    new_seq_no = int(msg[FTag.MsgSeqNum])

                    self.log.info(
                        "Received SequenceReset(GapFill) filling gap from %s to %s"
                        % (recv_seq_no, new_seq_no)
                    )
                self.session.set_recv_seq_no(int(new_seq_no) - 1)
                return False
        else:
            self.log.warning("Can't process message, counterparty is not logged in")

        return True

    async def _validate_seqnums(self, decoded_msg: FIXMessage) -> bool:
        recv_seq_no = int(decoded_msg[FTag.MsgSeqNum])
        last_seq_no = self.session.next_expected_msg_seq_num
        if recv_seq_no > last_seq_no:
            logging.info(
                "Requesting resend of messages: %s to %s" % (last_seq_no, sys.maxsize)
            )
            request = self.protocol.resend_request(last_seq_no, sys.maxsize)
            await self.send_msg(request)
            return False
        elif recv_seq_no < last_seq_no:
            self.log.warning(f'Received {recv_seq_no=} < {last_seq_no=}, critical')
            await self.disconnect()
            return False
        else:
            return True

    async def _process_message(self, decoded_msg: FIXMessage, raw_msg: bytes):
        protocol: FIXProtocolBase = self.codec.protocol
        self.log.debug(f"process_message (INCOMING)\n\t {decoded_msg}")

        msg_type = decoded_msg[FTag.MsgType]
        self.message_last_time = time.time()
        add_journal_msg = True

        try:
            if msg_type in protocol.session_message_types:
                add_journal_msg = await self.on_session_message(decoded_msg)

                if decoded_msg.msg_type == FMsg.LOGON:
                    await self.on_logon(decoded_msg)
                elif decoded_msg.msg_type == FMsg.LOGOUT:
                    await self.on_logout(decoded_msg)
                else:
                    # Check if seqnums are valid
                    if add_journal_msg and not await self._validate_seqnums(decoded_msg):
                        add_journal_msg = False
            else:
                if not await self._validate_seqnums(decoded_msg):
                    add_journal_msg = False
                else:
                    await self.on_message(decoded_msg)
        except asyncio.CancelledError:
            raise
        except Exception:
            self.log.exception("_process_message error: ")
            raise
        finally:
            if add_journal_msg:
                self.session.set_recv_seq_no(decoded_msg[FTag.MsgSeqNum])
                self.journaler.persist_msg(
                    raw_msg, self.session, MessageDirection.INBOUND
                )

    async def send_msg(self, msg: FIXMessage):
        if (
            self.connection_state != ConnectionState.CONNECTED
            and self.connection_state != ConnectionState.LOGGED_IN
        ):
            raise FIXConnectionError("FIXConnectionError is not connected or logged")

        encoded_msg = self.codec.encode(msg, self.session).encode("utf-8")

        msg_raw = encoded_msg.replace(b"\x01", b"|")
        self.log.debug(f"send_msg: (OUTBOUND)\n\t{msg_raw.decode()}")

        self.socket_writer.write(encoded_msg)
        await self.socket_writer.drain()

        self.journaler.persist_msg(encoded_msg, self.session, MessageDirection.OUTBOUND)
