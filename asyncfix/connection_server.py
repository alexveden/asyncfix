import asyncio
import logging
import asyncfix.FIX44 as FIXProtocol
from asyncfix.engine import FIXEngine
from asyncfix.message import FIXMessage
from asyncfix.journaler import DuplicateSeqNoError
from asyncfix.connection import (
    FIXEndPoint,
    ConnectionState,
    FIXConnectionHandler,
)


class FIXServerConnectionHandler(FIXConnectionHandler):
    def __init__(
        self,
        engine: FIXEngine,
        protocol: FIXProtocol,
        socket_reader: asyncio.StreamReader,
        socket_writer: asyncio.StreamWriter,
        addr=None,
        observer=None,
    ):
        FIXConnectionHandler.__init__(
            self, engine, protocol, socket_reader, socket_writer, addr, observer
        )

    async def handle_session_message(self, msg: FIXMessage):
        protocol = self.codec.protocol

        recv_seq_no = msg[protocol.fixtags.MsgSeqNum]

        msg_type = msg[protocol.fixtags.MsgType]
        target_comp_id = msg[protocol.fixtags.TargetCompID]
        sender_comp_id = msg[protocol.fixtags.SenderCompID]
        responses = []

        if msg_type == protocol.msgtype.LOGON:
            if self.connection_state == ConnectionState.LOGGED_IN:
                logging.warning(
                    "Client session already logged in - ignoring login request"
                )
            else:
                # compids are reversed here...
                self.session = self.engine.get_or_create_session_from_comp_ids(
                    sender_comp_id, target_comp_id
                )
                if self.session is not None:
                    try:
                        self.connection_state = ConnectionState.LOGGED_IN
                        self.heartbeat_period = float(msg[protocol.fixtags.HeartBtInt])
                        responses.append(protocol.logon())
                    except DuplicateSeqNoError:
                        logging.error(
                            "Failed to process login request with duplicate seq no"
                        )
                        await self.disconnect()
                        return
                else:
                    logging.warning(
                        "Rejected login attempt for invalid session (SenderCompId: %s,"
                        " TargetCompId: %s)" % (sender_comp_id, target_comp_id)
                    )
                    await self.disconnect()
                    return  # we have to return here since self.session won't be valid
        elif self.connection_state == ConnectionState.LOGGED_IN:
            # compids are reversed here
            if not self.session.validate_comp_ids(sender_comp_id, target_comp_id):
                logging.error("Received message with unexpected comp ids")
                await self.disconnect()
                return

            if msg_type == protocol.msgtype.LOGOUT:
                self.connection_state = ConnectionState.LOGGED_OUT
                self.handle_close()
            elif msg_type == protocol.msgtype.TESTREQUEST:
                responses.append(protocol.heartbeat())
            elif msg_type == protocol.msgtype.RESENDREQUEST:
                responses.extend(self._handle_resend_request(msg))
            elif msg_type == protocol.msgtype.SEQUENCERESET:
                new_seq_no = msg[protocol.fixtags.NewSeqNo]
                self.session.set_recv_seq_no(int(new_seq_no) - 1)
                recv_seq_no = new_seq_no
        else:
            logging.warning("Can't process message, counterparty is not logged in")

        return (recv_seq_no, responses)


class FIXServer(FIXEndPoint):
    def __init__(self, engine: FIXEngine, protocol: FIXProtocol):
        FIXEndPoint.__init__(self, engine, protocol)
        self.server = None

    async def start(self, host: str, port: int):
        self.connections = []
        self.server = await asyncio.start_server(self.handle_accept, host, port)

        logging.debug("Awaiting Connections " + host + ":" + str(port))
        async with self.server:
            await self.server.serve_forever()

    async def handle_accept(
        self, reader: asyncio.StreamReader, writer: asyncio.StreamWriter
    ):
        try:
            addr = writer.get_extra_info("peername")
            logging.info("Connection from %s" % repr(addr))

            connection = FIXServerConnectionHandler(
                self.engine, self.protocol, reader, writer, addr, self
            )
            self.connections.append(connection)
            for handler in filter(
                lambda x: x[1] == ConnectionState.CONNECTED, self.message_handlers
            ):
                await handler[0](connection)
        except Exception:
            logging.exception("handle_accept")
