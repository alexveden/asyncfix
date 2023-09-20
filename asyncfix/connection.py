import asyncio
import importlib
import logging
import sys
from enum import Enum
from typing import Callable

from asyncfix.codec import Codec
from asyncfix.engine import FIXEngine
from asyncfix.journaler import DuplicateSeqNoError
from asyncfix.message import FIXMessage, MessageDirection
from asyncfix.protocol import FIXProtocolBase
from asyncfix.session import FIXSession


class ConnectionState(Enum):
    UNKNOWN = 0
    DISCONNECTED = 1
    CONNECTED = 2
    LOGGED_IN = 3
    LOGGED_OUT = 4


class FIXException(Exception):
    class FIXExceptionReason(Enum):
        NOT_CONNECTED = 0
        DECODE_ERROR = 1
        ENCODE_ERROR = 2

    def __init__(self, reason, description=None):
        super(Exception, self).__init__(description)
        self.reason = reason


class SessionWarning(Exception):
    pass


class SessionError(Exception):
    pass


class FIXConnectionHandler(object):
    def __init__(
        self,
        engine: FIXEngine,
        protocol: FIXProtocolBase,
        socket_reader: asyncio.StreamReader,
        socket_writer: asyncio.StreamWriter,
        addr=None,
        observer=None,
    ):
        self.codec = Codec(protocol)
        self.engine = engine
        self.connection_state = ConnectionState.CONNECTED
        self.session: FIXSession | None = None
        self.addr = addr
        self.observer = observer
        self.msg_buffer = b""
        self.heartbeat_period = 30.0
        self.msg_handlers = []
        self.socket_reader = socket_reader
        self.socket_writer = socket_writer
        self.heartbeat_timer_registration = None
        self.expected_heartbeat_egistration = None
        # self.reader_task = asyncio.create_task(self.handle_read())

    def address(self):
        return self.addr

    async def disconnect(self):
        await self.handle_close()

    async def _notify_message_observers(
        self,
        msg: FIXMessage,
        direction: MessageDirection,
        persist_message=True,
    ):
        if persist_message is True:
            self.engine.journaller.persist_msg(msg, self.session, direction)
        for handler in filter(
            lambda x: (x[1] is None or x[1] == direction)
            and (x[2] is None or x[2] == msg.msg_type),
            self.msg_handlers,
        ):
            await handler[0](self, msg)

    def add_message_handler(
        self,
        handler: Callable,
        direction: MessageDirection | None = None,
        msg_type=None,
    ):
        self.msg_handlers.append((handler, direction, msg_type))

    def remove_message_handler(
        self,
        handler: Callable,
        direction: MessageDirection | None = None,
        msg_type=None,
    ):
        remove = filter(
            lambda x: x[0] == handler
            and (x[1] == direction or direction is None)
            and (x[2] == msg_type or msg_type is None),
            self.msg_handlers,
        )
        for h in remove:
            self.msg_handlers.remove(h)

    def _send_heartbeat(self):
        self.send_msg(self.codec.protocol.heartbeat())

    def _expected_heartbeat(self, type, closure):
        logging.warning(
            "Expected heartbeat from peer %s" % (self.expected_heartbeat_egistration,)
        )
        self.send_msg(self.codec.protocol.test_request())

    def _handle_resend_request(self, msg: FIXMessage):
        protocol: FIXProtocolBase = self.codec.protocol
        responses = []

        begin_seq_no = msg[protocol.fixtags.BeginSeqNo]
        end_seq_no = msg[protocol.fixtags.EndSeqNo]
        if int(end_seq_no) == 0:
            end_seq_no = sys.maxsize
        logging.info("Received resent request from %s to %s", begin_seq_no, end_seq_no)
        replay_msgs = self.engine.journaller.recover_msgs(
            self.session, MessageDirection.OUTBOUND, begin_seq_no, end_seq_no
        )
        gap_fill_begin = int(begin_seq_no)
        gap_fill_end = int(begin_seq_no)
        for replay_msg in replay_msgs:
            msg_seq_num = int(replay_msg[protocol.fixtags.MsgSeqNum])
            if replay_msg[protocol.fixtags.MsgType] in protocol.session_message_types:
                gap_fill_end = msg_seq_num + 1
            else:
                if self.engine.should_resend_message(self.session, replay_msg):
                    if gap_fill_begin < gap_fill_end:
                        # we need to send a gap fill message
                        gap_fill_msg = FIXMessage(protocol.msgtype.SEQUENCERESET)
                        gap_fill_msg.set(protocol.fixtags.GapFillFlag, "Y")
                        gap_fill_msg.set(protocol.fixtags.MsgSeqNum, gap_fill_begin)
                        gap_fill_msg.set(protocol.fixtags.NewSeqNo, str(gap_fill_end))
                        responses.append(gap_fill_msg)

                    # and then resent the replayMsg
                    replay_msg.removeField(protocol.fixtags.BeginString)
                    replay_msg.removeField(protocol.fixtags.BodyLength)
                    replay_msg.removeField(protocol.fixtags.SendingTime)
                    replay_msg.removeField(protocol.fixtags.SenderCompID)
                    replay_msg.removeField(protocol.fixtags.TargetCompID)
                    replay_msg.removeField(protocol.fixtags.CheckSum)
                    replay_msg.setField(protocol.fixtags.PossDupFlag, "Y")
                    responses.append(replay_msg)

                    gap_fill_begin = msg_seq_num + 1
                else:
                    gap_fill_end = msg_seq_num + 1
                    responses.append(replay_msg)

        if gap_fill_begin < gap_fill_end:
            # we need to send a gap fill message
            gap_fill_msg = FIXMessage(protocol.msgtype.SEQUENCERESET)
            gap_fill_msg.set(protocol.fixtags.GapFillFlag, "Y")
            gap_fill_msg.set(protocol.fixtags.MsgSeqNum, gap_fill_begin)
            gap_fill_msg.set(protocol.fixtags.NewSeqNo, str(gap_fill_end))
            responses.append(gap_fill_msg)

        return responses

    async def handle_read(self):
        logging.debug("handle_read")
        while True:
            try:
                msg = await self.socket_reader.read(4096)
                if not msg:
                    raise ConnectionError
                # breakpoint()

                self.msg_buffer = self.msg_buffer + msg
                while True:
                    if self.connection_state == ConnectionState.DISCONNECTED:
                        break

                    (decoded_msg, parsed_length) = self.codec.decode(self.msg_buffer)

                    if parsed_length > 0:
                        self.msg_buffer = self.msg_buffer[parsed_length:]

                    if decoded_msg is None:
                        break

                    await self.process_message(decoded_msg)
            except asyncio.CancelledError:
                break
            except ConnectionError as why:
                logging.debug("Connection has been closed %s" % (why,))
                await self.disconnect()
                return
            except Exception:
                logging.exception("handle_read failed")
                raise

    async def handle_session_message(self, msg: FIXMessage):
        return -1

    async def process_message(self, decoded_msg: FIXMessage):
        protocol: FIXProtocolBase = self.codec.protocol
        logging.debug(f"processMessage \n\t {decoded_msg}")

        begin_string = decoded_msg[protocol.fixtags.BeginString]
        if begin_string != protocol.beginstring:
            logging.warning(
                "FIX BeginString is incorrect (expected: %s received: %s)",
                (protocol.beginstring, begin_string),
            )
            await self.disconnect()
            return

        msg_type = decoded_msg[protocol.fixtags.MsgType]

        try:
            responses = []
            if msg_type in protocol.session_message_types:
                (recv_seq_no, responses) = await self.handle_session_message(
                    decoded_msg
                )
            else:
                recv_seq_no = decoded_msg[protocol.fixtags.MsgSeqNum]

            # validate the seq number
            (seq_no_state, last_known_seq_no) = self.session.validate_recv_seq_no(
                recv_seq_no
            )

            if seq_no_state is False:
                # We should send a resend request
                logging.info(
                    "Requesting resend of messages: %s to %s" % (last_known_seq_no, 0)
                )
                responses.append(protocol.resend_request(last_known_seq_no, 0))
                # we still need to notify if we are processing Logon message
                if msg_type == protocol.msgtype.LOGON:
                    await self._notify_message_observers(
                        decoded_msg, MessageDirection.INBOUND, False
                    )
            else:
                self.session.set_recv_seq_no(recv_seq_no)
                await self._notify_message_observers(
                    decoded_msg, MessageDirection.INBOUND
                )

            for m in responses:
                await self.send_msg(m)

        except SessionWarning as sw:
            logging.warning(sw)
        except SessionError as se:
            logging.error(se)
            await self.disconnect()
        except DuplicateSeqNoError:
            try:
                if decoded_msg[protocol.fixtags.PossDupFlag] == "Y":
                    logging.debug("Received duplicate message with PossDupFlag set")
            except KeyError:
                pass
            finally:
                logging.error(
                    "Failed to process message with duplicate seq no (MsgSeqNum: %s)"
                    " (and no PossDupFlag='Y') - disconnecting" % (recv_seq_no,)
                )
                await self.disconnect()

    async def handle_close(self):
        if self.connection_state != ConnectionState.DISCONNECTED:
            logging.info("Client disconnected")
            self.socket_writer.close()
            self.connection_state = ConnectionState.DISCONNECTED
            self.msg_handlers.clear()
            if self.observer is not None:
                await self.observer.notify_disconnect(self)

    async def send_msg(self, msg: FIXMessage):
        if (
            self.connection_state != ConnectionState.CONNECTED
            and self.connection_state != ConnectionState.LOGGED_IN
        ):
            logging.debug("sendMsg not connected or logged in")
            return

        encoded_msg = self.codec.encode(msg, self.session).encode("utf-8")
        self.socket_writer.write(encoded_msg)
        await self.socket_writer.drain()
        decoded_msg, junk = self.codec.decode(encoded_msg)
        logging.debug(f"send msg sending msg\n\t {decoded_msg}")

        try:
            await self._notify_message_observers(decoded_msg, MessageDirection.OUTBOUND)
        except DuplicateSeqNoError:
            logging.error(
                "We have sent a message with a duplicate seq no, failed to persist it"
                " (MsgSeqNum: %s)"
                % (decoded_msg[self.codec.protocol.fixtags.MsgSeqNum])
            )


class FIXEndPoint(object):
    def __init__(self, engine: FIXEngine, protocol: FIXProtocolBase):
        self.engine: FIXEngine = engine
        self.protocol: FIXProtocolBase = importlib.import_module(protocol)

        self.connections: list[FIXConnectionHandler] = []
        self.message_handlers = []

    def writable(self):
        return True

    def start(self, host, port, loop):
        pass

    def stop(self):
        pass

    def add_connection_listener(self, handler: Callable, filter):
        self.message_handlers.append((handler, filter))

    def remove_connection_listener(self, handler: Callable, filter):
        for s in self.message_handlers:
            if s == (handler, filter):
                self.message_handlers.remove(s)

    async def notify_disconnect(self, connection: FIXConnectionHandler):
        self.connections.remove(connection)
        for handler in filter(
            lambda x: x[1] == ConnectionState.DISCONNECTED, self.message_handlers
        ):
            await handler[0](connection)
