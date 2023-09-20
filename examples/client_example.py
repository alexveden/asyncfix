import asyncio
from enum import Enum
import logging
import random
from asyncfix.connection import ConnectionState, MessageDirection, FIXConnectionHandler
from asyncfix.connection_client import FIXClient
from asyncfix.engine import FIXEngine
from asyncfix.message import FIXMessage


class Side(Enum):
    buy = 1
    sell = 2


class Client(FIXEngine):
    def __init__(self):
        FIXEngine.__init__(self, "client_example.store")
        self.clOrdID = 0
        self.msgGenerator = None
        # create a FIX Client using the FIX 4.4 standard
        self.client = FIXClient(self, "asyncfix.FIX44", "TARGET", "SENDER")
        self.client.add_connection_listener(self.on_connect, ConnectionState.CONNECTED)
        self.client.add_connection_listener(
            self.on_disconnect, ConnectionState.DISCONNECTED
        )

    async def start(self, host: str, port: int):
        await self.client.start(host, port)

        while True:
            # Must we await loop!  client would not be processing data without it
            await asyncio.sleep(1)

    async def on_connect(self, session: FIXConnectionHandler):
        logging.info("Established connection to %s" % (session.address(),))

        session.add_message_handler(
            self.on_login, MessageDirection.INBOUND, self.client.protocol.msgtype.LOGON
        )
        session.add_message_handler(
            self.on_execution_report,
            MessageDirection.INBOUND,
            self.client.protocol.msgtype.EXECUTIONREPORT,
        )

    async def on_disconnect(self, session: FIXConnectionHandler):
        logging.info("%s has disconnected" % (session.address(),))

        # we need to clean up our handlers, since this session is disconnected now
        session.remove_message_handler(
            self.on_login, MessageDirection.INBOUND, self.client.protocol.msgtype.LOGON
        )
        session.remove_message_handler(
            self.on_execution_report,
            MessageDirection.INBOUND,
            self.client.protocol.msgtype.EXECUTIONREPORT,
        )

    async def send_order(self, connection: FIXConnectionHandler):
        self.clOrdID = self.clOrdID + 1
        codec = connection.codec
        msg = FIXMessage(codec.protocol.msgtype.NEWORDERSINGLE)
        msg.set(codec.protocol.fixtags.Price, "%0.2f" % (random.random() * 2 + 10))
        msg.set(codec.protocol.fixtags.OrderQty, int(random.random() * 100))
        msg.set(codec.protocol.fixtags.Symbol, "VOD.L")
        msg.set(codec.protocol.fixtags.SecurityID, "GB00BH4HKS39")
        msg.set(codec.protocol.fixtags.SecurityIDSource, "4")
        msg.set(codec.protocol.fixtags.Account, "TEST")
        msg.set(codec.protocol.fixtags.HandlInst, "1")
        msg.set(codec.protocol.fixtags.ExDestination, "XLON")
        msg.set(codec.protocol.fixtags.Side, int(random.random() * 2) + 1)
        msg.set(codec.protocol.fixtags.ClOrdID, str(self.clOrdID))
        msg.set(codec.protocol.fixtags.Currency, "GBP")

        await connection.send_msg(msg)
        side = Side(int(msg.get(codec.protocol.fixtags.Side)))
        logging.debug(
            "---> [%s] %s: %s %s %s@%s"
            % (
                codec.protocol.msgtype.msgTypeToName(msg.msg_type),
                msg.get(codec.protocol.fixtags.ClOrdID),
                msg.get(codec.protocol.fixtags.Symbol),
                side.name,
                msg.get(codec.protocol.fixtags.OrderQty),
                msg.get(codec.protocol.fixtags.Price),
            )
        )

    async def on_login(self, connection: FIXConnectionHandler, msg: FIXMessage):
        logging.info("Logged in")
        await self.send_order(connection)

    async def on_execution_report(
        self, connection: FIXConnectionHandler, msg: FIXMessage
    ):
        codec = connection.codec

        if codec.protocol.fixtags.ExecType in msg:
            if msg.get(codec.protocol.fixtags.ExecType) == "0":
                side = Side(int(msg.get(codec.protocol.fixtags.Side)))

                logging.debug(
                    "<--- [%s] %s: %s %s %s@%s"
                    % (
                        codec.protocol.msgtype.msgTypeToName(
                            msg.get(codec.protocol.fixtags.MsgType)
                        ),
                        msg.get(codec.protocol.fixtags.ClOrdID),
                        msg.get(codec.protocol.fixtags.Symbol),
                        side.name,
                        msg.get(codec.protocol.fixtags.OrderQty),
                        msg.get(codec.protocol.fixtags.Price),
                    )
                )
            elif msg.get(codec.protocol.fixtags.ExecType) == "4":
                reason = (
                    "Unknown"
                    if codec.protocol.fixtags.Text not in msg
                    else msg.get(codec.protocol.fixtags.Text)
                )
                logging.info("Order Rejected '%s'" % (reason,))
        else:
            logging.error("Received execution report without ExecType")


if __name__ == "__main__":
    logging.basicConfig(
        level=logging.DEBUG,
        format="%(asctime)s [%(filename)20s:%(lineno)-4s] %(levelname)5s - %(message)s",
    )

    loop = asyncio.get_event_loop()
    client = Client()
    asyncio.run(client.start("localhost", 9898))
    loop.run_forever()
