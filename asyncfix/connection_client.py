import asyncio
import logging
import asyncfix.FIX44 as FIXProtocol
from asyncfix.message import FIXMessage
from asyncfix.journaler import DuplicateSeqNoError
from asyncfix.engine import FIXEngine
from asyncfix.connection import (
    FIXEndPoint,
    ConnectionState,
    FIXConnectionHandler,
)


class FIXClientConnectionHandler(FIXConnectionHandler):
    def __init__(
        self,
        engine: FIXEngine,
        protocol: FIXProtocol,
        target_comp_id: str,
        sender_comp_id: str,
        socket_reader: asyncio.StreamReader,
        socket_writer: asyncio.StreamWriter,
        addr=None,
        observer=None,
        target_sub_id=None,
        sender_sub_id=None,
        heartbeat_timeout=30,
        heartbeat=1,
    ):
        super().__init__(
            engine=engine,
            protocol=protocol,
            socket_reader=socket_reader,
            socket_writer=socket_writer,
            addr=addr,
            observer=observer,
        )

        self.target_comp_id = target_comp_id
        self.sender_comp_id = sender_comp_id
        self.target_sub_id = target_sub_id
        self.sender_sub_id = sender_sub_id
        self.heartbeat_period = float(heartbeat_timeout)
        self.heartbeat = heartbeat

        # we need to send a login request.
        self.session = self.engine.get_or_create_session_from_comp_ids(
            self.target_comp_id, self.sender_comp_id
        )
        if self.session is None:
            raise RuntimeError("Failed to create client session")

        self.protocol = protocol

        asyncio.ensure_future(self.logon())

    async def logon(self):
        logon_msg = self.protocol.logon()
        logon_msg.set(self.protocol.fixtags.HeartBtInt, self.heartbeat)
        await self.send_msg(logon_msg)

    async def handle_session_message(self, msg: FIXMessage):
        protocol = self.codec.protocol
        responses = []

        recv_seq_no = msg[protocol.fixtags.MsgSeqNum]

        msg_type = msg[protocol.fixtags.MsgType]
        target_comp_d = msg[protocol.fixtags.TargetCompID]
        sender_comp_id = msg[protocol.fixtags.SenderCompID]

        if msg_type == protocol.msgtype.LOGON:
            if self.connection_state == ConnectionState.LOGGED_IN:
                logging.warning(
                    "Client session already logged in - ignoring login request"
                )
            else:
                try:
                    self.connection_state = ConnectionState.LOGGED_IN
                    self.heartbeat_period = float(msg[protocol.fixtags.HeartBtInt])
                except DuplicateSeqNoError:
                    logging.error(
                        "Failed to process login request with duplicate seq no"
                    )
                    await self.disconnect()
                    return
        elif self.connection_state == ConnectionState.LOGGED_IN:
            # compids are reversed here
            if not self.session.validate_comp_ids(sender_comp_id, target_comp_d):
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
                # we can treat GapFill and SequenceReset in the same way
                # in both cases we will just reset the seq number to the
                # NewSeqNo received in the message
                new_seq_no = msg[protocol.fixtags.NewSeqNo]
                if msg[protocol.fixtags.GapFillFlag] == "Y":
                    logging.info(
                        "Received SequenceReset(GapFill) filling gap from %s to %s"
                        % (recv_seq_no, new_seq_no)
                    )
                self.session.set_recv_seq_no(int(new_seq_no) - 1)
                recv_seq_no = new_seq_no
        else:
            logging.warning("Can't process message, counterparty is not logged in")

        return (recv_seq_no, responses)


class FIXClient(FIXEndPoint):
    def __init__(
        self,
        engine: FIXEngine,
        protocol: FIXProtocol,
        target_comp_id,
        sender_comp_id,
        target_sub_id=None,
        sender_sub_id=None,
        heartbeat_timeout=30,
        with_seq_no_reset=True,
    ):
        self.target_comp_id = target_comp_id
        self.sender_comp_id = sender_comp_id
        self.target_sub_id = target_sub_id
        self.sender_sub_id = sender_sub_id
        self.heartbeat_timeout = heartbeat_timeout
        self.with_seq_no_reset = with_seq_no_reset
        self.socket_reader = self.socket_writer = None
        self.addr = None

        FIXEndPoint.__init__(self, engine, protocol)

    async def start(self, host, port):
        self.socket_reader, self.socket_writer = await asyncio.open_connection(
            host, port
        )
        self.addr = (host, port)

        logging.info("Connected to %s" % repr(self.addr))
        connection = FIXClientConnectionHandler(
            engine=self.engine,
            protocol=self.protocol,
            target_comp_id=self.target_comp_id,
            sender_comp_id=self.sender_comp_id,
            socket_reader=self.socket_reader,
            socket_writer=self.socket_writer,
            addr=self.addr,
            observer=self,
            target_sub_id=self.target_sub_id,
            sender_sub_id=self.sender_sub_id,
            heartbeat_timeout=self.heartbeat_timeout,
        )

        self.connections.append(connection)

        for handler in filter(
            lambda x: x[1] == ConnectionState.CONNECTED, self.message_handlers
        ):
            await handler[0](connection)

    def stop(self):
        logging.info("Stopping client connections")
        for connection in self.connections:
            connection.disconnect()
        self.socket_writer.close()
