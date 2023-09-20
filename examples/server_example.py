import asyncio
from enum import Enum
import logging
from asyncfix.connection import ConnectionState, MessageDirection, FIXConnectionHandler
from asyncfix.engine import FIXEngine
from asyncfix.message import FIXMessage
from asyncfix.connection_server import FIXServer


class Side(Enum):
    buy = 1
    sell = 2


class Server(FIXEngine):
    def __init__(self):
        FIXEngine.__init__(self, "server_example.store")
        # create a FIX Server using the FIX 4.4 standard
        self.server = FIXServer(self, "asyncfix.FIX44")

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
        codec = connection_handler.codec
        logging.info(
            "onLogin ["
            + msg[codec.protocol.fixtags.SenderCompID]
            + "] <---- "
            + codec.protocol.msgtype.msgTypeToName(msg[codec.protocol.fixtags.MsgType])
        )

    async def on_new_order(self, connection: FIXConnectionHandler, request: FIXMessage):
        codec = connection.codec
        try:
            side = Side(int(request.get(codec.protocol.fixtags.Side)))
            logging.debug(
                "<--- [%s] %s: %s %s %s@%s"
                % (
                    codec.protocol.msgtype.msgTypeToName(
                        request.get(codec.protocol.fixtags.MsgType)
                    ),
                    request.get(codec.protocol.fixtags.ClOrdID),
                    request.get(codec.protocol.fixtags.Symbol),
                    side.name,
                    request.get(codec.protocol.fixtags.OrderQty),
                    request.get(codec.protocol.fixtags.Price),
                )
            )

            # respond with an ExecutionReport Ack
            msg = FIXMessage(codec.protocol.msgtype.EXECUTIONREPORT)
            msg.set(
                codec.protocol.fixtags.Price,
                request.get(codec.protocol.fixtags.Price),
            )
            msg.set(
                codec.protocol.fixtags.OrderQty,
                request.get(codec.protocol.fixtags.OrderQty),
            )
            msg.set(
                codec.protocol.fixtags.Symbol,
                request.get(codec.protocol.fixtags.OrderQty),
            )

            msg.set(codec.protocol.fixtags.SecurityID, "GB00BH4HKS39")
            msg.set(codec.protocol.fixtags.SecurityIDSource, "4")
            msg.set(
                codec.protocol.fixtags.Symbol,
                request.get(codec.protocol.fixtags.Symbol),
            )
            msg.set(
                codec.protocol.fixtags.Account,
                request.get(codec.protocol.fixtags.Account),
            )
            msg.set(codec.protocol.fixtags.HandlInst, "1")
            msg.set(codec.protocol.fixtags.OrdStatus, "0")
            msg.set(codec.protocol.fixtags.ExecType, "0")
            msg.set(codec.protocol.fixtags.LeavesQty, "0")
            msg.set(
                codec.protocol.fixtags.Side,
                request.get(codec.protocol.fixtags.Side),
            )
            msg.set(
                codec.protocol.fixtags.ClOrdID,
                request.get(codec.protocol.fixtags.ClOrdID),
            )
            msg.set(
                codec.protocol.fixtags.Currency,
                request.get(codec.protocol.fixtags.Currency),
            )

            await connection.send_msg(msg)

            logging.debug(
                "---> [%s] %s: %s %s %s@%s"
                % (
                    codec.protocol.msgtype.msgTypeToName(msg.msg_type),
                    msg.get(codec.protocol.fixtags.ClOrdID),
                    request.get(codec.protocol.fixtags.Symbol),
                    side.name,
                    request.get(codec.protocol.fixtags.OrderQty),
                    request.get(codec.protocol.fixtags.Price),
                )
            )

        except Exception as e:
            msg = FIXMessage(codec.protocol.msgtype.EXECUTIONREPORT)
            msg.set(codec.protocol.fixtags.OrdStatus, "4")
            msg.set(codec.protocol.fixtags.ExecType, "4")
            msg.set(codec.protocol.fixtags.LeavesQty, "0")
            msg.set(codec.protocol.fixtags.Text, str(e))
            msg.set(
                codec.protocol.fixtags.ClOrdID,
                request.get(codec.protocol.fixtags.ClOrdID),
            )

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
