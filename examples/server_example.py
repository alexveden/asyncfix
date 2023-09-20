import asyncio
import logging
from enum import Enum

from asyncfix import FIXMessage, FMsg, FTag
from asyncfix.connection import ConnectionState, FIXConnectionHandler, MessageDirection
from asyncfix.connection_server import FIXServer
from asyncfix.engine import FIXEngine
from asyncfix.protocol.protocol_fix44 import FIXProtocol44


class Side(Enum):
    buy = 1
    sell = 2


class Server(FIXEngine):
    def __init__(self):
        FIXEngine.__init__(self, "server_example.store")
        # create a FIX Server using the FIX 4.4 standard
        self.server = FIXServer(self, FIXProtocol44())

        # we register some listeners since we want to know when
        #    the connection goes up or down
        self.server.add_connection_listener(self.on_connect, ConnectionState.CONNECTED)
        self.server.add_connection_listener(
            self.on_disconnect, ConnectionState.DISCONNECTED
        )
        # start our event listener indefinitely

    async def start(self, host, port):
        await self.server.start(host, port)

    def validate_session(self, target_comp_id, sender_comp_id):
        logging.info(
            "Received login request for %s / %s" % (sender_comp_id, target_comp_id)
        )
        return True

    async def on_connect(self, connection: FIXConnectionHandler):
        logging.info("Accepted new connection from %s" % (connection.address(),))

        # register to receive message notifications on the session
        #  which has just been created
        connection.add_message_handler(
            self.on_login, MessageDirection.OUTBOUND, self.server.protocol.msgtype.LOGON
        )
        connection.add_message_handler(
            self.on_new_order,
            MessageDirection.INBOUND,
            self.server.protocol.msgtype.NEWORDERSINGLE,
        )

    async def on_disconnect(self, connection: FIXConnectionHandler):
        logging.info("%s has disconnected" % (connection.address(),))

        # we need to clean up our handlers, since this session is disconnected now
        connection.remove_message_handler(
            self.on_login, MessageDirection.OUTBOUND, self.server.protocol.msgtype.LOGON
        )
        connection.remove_message_handler(
            self.on_new_order,
            MessageDirection.INBOUND,
            self.server.protocol.msgtype.NEWORDERSINGLE,
        )

    async def on_login(self, connection_handler: FIXConnectionHandler, msg: FIXMessage):
        logging.info(
            "onLogin [" + msg[FTag.SenderCompID] + "] <---- " + msg[FTag.MsgType]
        )

    async def on_new_order(self, connection: FIXConnectionHandler, request: FIXMessage):
        try:
            side = Side(int(request.get(FTag.Side)))
            logging.debug(
                "<--- [%s] %s: %s %s %s@%s"
                % (
                    request.get(FTag.MsgType),
                    request.get(FTag.ClOrdID),
                    request.get(FTag.Symbol),
                    side.name,
                    request.get(FTag.OrderQty),
                    request.get(FTag.Price),
                )
            )

            # respond with an ExecutionReport Ack
            msg = FIXMessage(FMsg.EXECUTIONREPORT)
            msg.set(FTag.Price, request.get(FTag.Price))
            msg.set(FTag.OrderQty, request.get(FTag.OrderQty))
            msg.set(FTag.Symbol, request.get(FTag.OrderQty))

            msg.set(FTag.SecurityID, "GB00BH4HKS39")
            msg.set(FTag.SecurityIDSource, "4")
            msg.set(FTag.Symbol, request.get(FTag.Symbol))
            msg.set(FTag.Account, request.get(FTag.Account))
            msg.set(FTag.HandlInst, "1")
            msg.set(FTag.OrdStatus, "0")
            msg.set(FTag.ExecType, "0")
            msg.set(FTag.LeavesQty, "0")
            msg.set(FTag.Side, request.get(FTag.Side))
            msg.set(FTag.ClOrdID, request.get(FTag.ClOrdID))
            msg.set(FTag.Currency, request.get(FTag.Currency))

            await connection.send_msg(msg)

            logging.debug(
                "---> [%s] %s: %s %s %s@%s"
                % (
                    msg.msg_type,
                    msg.get(FTag.ClOrdID),
                    request.get(FTag.Symbol),
                    side.name,
                    request.get(FTag.OrderQty),
                    request.get(FTag.Price),
                )
            )

        except Exception as e:
            msg = FIXMessage(FMsg.EXECUTIONREPORT)
            msg.set(FTag.OrdStatus, "4")
            msg.set(FTag.ExecType, "4")
            msg.set(FTag.LeavesQty, "0")
            msg.set(FTag.Text, str(e))
            msg.set(FTag.ClOrdID, request.get(FTag.ClOrdID))

            await connection.send_msg(msg)


if __name__ == "__main__":
    logging.basicConfig(
        level=logging.DEBUG,
        format="%(asctime)s [%(filename)20s:%(lineno)-4s] %(levelname)5s - %(message)s",
    )
    loop = asyncio.get_event_loop()
    server = Server()
    asyncio.run(server.start("localhost", 9898))
    loop.run_forever()
