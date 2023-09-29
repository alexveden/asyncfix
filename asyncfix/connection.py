import asyncio
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
                if self.connection_state == ConnectionState.LOGGED_IN:
                    if time.time() - self.message_last_time > self.heartbeat_period - 1:
                        await self.send_msg(self.protocol.heartbeat())
                        self.message_last_time = time.time()

            except asyncio.CancelledError:
                raise
            except Exception:
                logging.exception("heartbeat_timer() error")
            await asyncio.sleep(1.0)

    async def on_session_message(self, msg: FIXMessage):
        raise NotImplementedError("on_session_message not implemented in child")

    async def on_message(self, msg: FIXMessage):
        raise NotImplementedError("on_message not implemented in child")

    async def on_connect(self):
        raise NotImplementedError("on_connected not implemented in child")

    async def on_disconnect(self):
        raise NotImplementedError("on_disconnected not implemented in child")

    async def on_logon(self, msg: FIXMessage):
        raise NotImplementedError("on_logon not implemented in child")

    async def on_logout(self, msg: FIXMessage):
        raise NotImplementedError("on_logout not implemented in child")

    async def _validate_seqnums(self, decoded_msg: FIXMessage) -> bool:
        recv_seq_no = decoded_msg[FTag.MsgSeqNum]

        (seq_no_valid, last_seq_no) = self.session.validate_recv_seq_no(recv_seq_no)

        if not seq_no_valid:
            # We should send a resend request
            logging.info("Requesting resend of messages: %s to %s" % (last_seq_no, 0))
            request = self.protocol.resend_request(last_seq_no, 0)
            await self.send_msg(request)

        return seq_no_valid

    async def _process_message(self, decoded_msg: FIXMessage, raw_msg: bytes):
        protocol: FIXProtocolBase = self.codec.protocol
        self.log.debug(f"process_message \n\t {decoded_msg}")

        msg_type = decoded_msg[FTag.MsgType]
        self.message_last_time = time.time()
        add_journal_msg = True

        try:
            if msg_type in protocol.session_message_types:
                await self.on_session_message(decoded_msg)

                if decoded_msg.msg_type == FMsg.LOGON:
                    await self.on_logon(decoded_msg)
                elif decoded_msg.msg_type == FMsg.LOGOUT:
                    await self.on_logout(decoded_msg)
                else:
                    # Check if seqnums are valid
                    if not await self._validate_seqnums(decoded_msg):
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
        self.log.debug(f"send_msg: \n\t{msg_raw.decode()}")

        self.socket_writer.write(encoded_msg)
        await self.socket_writer.drain()

        self.journaler.persist_msg(encoded_msg, self.session, MessageDirection.OUTBOUND)
