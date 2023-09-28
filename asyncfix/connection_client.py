import asyncio
import logging

from asyncfix import FMsg, FTag
from asyncfix.connection import ConnectionState, FIXConnectionHandler, FIXEndPoint
from asyncfix.engine import FIXEngine
from asyncfix.journaler import DuplicateSeqNoError
from asyncfix.message import FIXMessage
from asyncfix.protocol import FIXProtocolBase
import time


class FIXClientConnectionHandler(FIXConnectionHandler):
    def __init__(
        self,
        engine: FIXEngine,
        protocol: FIXProtocolBase,
        target_comp_id: str,
        sender_comp_id: str,
        socket_reader: asyncio.StreamReader,
        socket_writer: asyncio.StreamWriter,
        addr=None,
        observer=None,
        target_sub_id=None,
        sender_sub_id=None,
        heartbeat_timeout=30,
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
        self.message_last_time = 0.0
        assert heartbeat_timeout > 5, 'heartbeat_timeout is too low'

        # we need to send a login request.
        self.session = self.engine.get_or_create_session_from_comp_ids(
            self.target_comp_id, self.sender_comp_id
        )
        if self.session is None:
            raise RuntimeError("Failed to create client session")

        self.protocol = protocol

    async def heartbeat_timer(self):
        while True:
            try:
                if self.connection_state == ConnectionState.LOGGED_IN:
                    if time.time() - self.message_last_time > self.heartbeat_period-1:
                        await self.send_msg(self.protocol.heartbeat())
                        self.message_last_time = time.time()

            except asyncio.CancelledError:
                raise
            except Exception:
                logging.exception('heartbeat_timer() error')
            await asyncio.sleep(1.0)

    async def logon(self, reset_seq_num: bool = False):
        logon_msg = self.protocol.logon()
        logon_msg.set(FTag.HeartBtInt, int(self.heartbeat_period), replace=True)
        logon_msg.set(FTag.ResetSeqNumFlag, "Y" if reset_seq_num else "N", replace=True)
        await self.send_msg(logon_msg)

    async def handle_session_message(self, msg: FIXMessage):
        responses = []

        recv_seq_no = msg[FTag.MsgSeqNum]

        msg_type = msg[FTag.MsgType]
        target_comp_d = msg[FTag.TargetCompID]
        sender_comp_id = msg[FTag.SenderCompID]

        if msg_type == FMsg.LOGON:
            if self.connection_state == ConnectionState.LOGGED_IN:
                logging.warning(
                    "Client session already logged in - ignoring login request"
                )
            else:
                self.connection_state = ConnectionState.LOGGED_IN
                self.heartbeat_period = float(msg[FTag.HeartBtInt])
        elif self.connection_state == ConnectionState.LOGGED_IN:
            self.message_last_time = time.time()
            # compids are reversed here
            if not self.session.validate_comp_ids(sender_comp_id, target_comp_d):
                logging.error("Received message with unexpected comp ids")
                await self.disconnect()
                return

            if msg_type == FMsg.LOGOUT:
                self.connection_state = ConnectionState.LOGGED_OUT
                await self.handle_close()
            elif msg_type == FMsg.TESTREQUEST:
                # https://www.fixtrading.org/standards/fix-session-layer-online/#message-exchange-during-a-fix-connection # noqa
                #    see "Test request processing" section
                #  required to reply with TestReqID from query
                hbt_msg = self.protocol.heartbeat()
                hbt_msg[FTag.TestReqID] = msg[FTag.TestReqID]
                responses.append(hbt_msg)
            elif msg_type == FMsg.RESENDREQUEST:
                responses.extend(self._handle_resend_request(msg))
            elif msg_type == FMsg.SEQUENCERESET:
                # we can treat GapFill and SequenceReset in the same way
                # in both cases we will just reset the seq number to the
                # NewSeqNo received in the message
                new_seq_no = msg[FTag.NewSeqNo]
                if msg[FTag.GapFillFlag] == "Y":
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
        protocol: FIXProtocolBase,
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
        asyncio.create_task(connection.handle_read())
        asyncio.create_task(connection.logon())
        asyncio.create_task(connection.heartbeat_timer())

        self.connections.append(connection)

        for handler in filter(
            lambda x: x[1] == ConnectionState.CONNECTED, self.message_handlers
        ):
            await handler[0](connection)

    async def stop(self):
        logging.info("Stopping client connections")
        for connection in self.connections:
            await connection.disconnect()
        self.connections.clear()
        self.socket_writer.close()
