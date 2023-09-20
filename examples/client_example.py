import asyncio
import logging
import random
from enum import Enum

from asyncfix import FIXMessage, FMsg, FTag
from asyncfix.connection import ConnectionState, FIXConnectionHandler, MessageDirection
from asyncfix.connection_client import FIXClient
from asyncfix.engine import FIXEngine
from asyncfix.protocol.protocol_fix44 import FIXProtocol44


class Side(Enum):
    buy = 1
    sell = 2


class Client(FIXEngine):
    def __init__(self):
        FIXEngine.__init__(self, "client_example.store")
        self.clOrdID = 0
        self.msgGenerator = None
        # create a FIX Client using the FIX 4.4 standard
        self.client = FIXClient(self, FIXProtocol44(), "TARGET", "SENDER")
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

        session.add_message_handler(self.on_login, MessageDirection.INBOUND, FMsg.LOGON)
        session.add_message_handler(
            self.on_execution_report,
            MessageDirection.INBOUND,
            FMsg.EXECUTIONREPORT,
        )

    async def on_disconnect(self, session: FIXConnectionHandler):
        logging.info("%s has disconnected" % (session.address(),))

        # we need to clean up our handlers, since this session is disconnected now
        session.remove_message_handler(
            self.on_login, MessageDirection.INBOUND, FMsg.LOGON
        )
        session.remove_message_handler(
            self.on_execution_report,
            MessageDirection.INBOUND,
            self.client.protocol.msgtype.EXECUTIONREPORT,
        )

    async def send_order(self, connection: FIXConnectionHandler):
        self.clOrdID = self.clOrdID + 1
        msg = FIXMessage(FMsg.NEWORDERSINGLE)
        msg.set(FTag.Price, "%0.2f" % (random.random() * 2 + 10))
        msg.set(FTag.OrderQty, int(random.random() * 100))
        msg.set(FTag.Symbol, "VOD.L")
        msg.set(FTag.SecurityID, "GB00BH4HKS39")
        msg.set(FTag.SecurityIDSource, "4")
        msg.set(FTag.Account, "TEST")
        msg.set(FTag.HandlInst, "1")
        msg.set(FTag.ExDestination, "XLON")
        msg.set(FTag.Side, int(random.random() * 2) + 1)
        msg.set(FTag.ClOrdID, str(self.clOrdID))
        msg.set(FTag.Currency, "GBP")

        await connection.send_msg(msg)
        side = Side(int(msg.get(FTag.Side)))
        logging.debug(
            "---> [%s] %s: %s %s %s@%s"
            % (
                msg.msg_type,
                msg.get(FTag.ClOrdID),
                msg.get(FTag.Symbol),
                side.name,
                msg.get(FTag.OrderQty),
                msg.get(FTag.Price),
            )
        )

    async def on_login(self, connection: FIXConnectionHandler, msg: FIXMessage):
        logging.info("Logged in")
        await self.send_order(connection)

    async def on_execution_report(
        self, connection: FIXConnectionHandler, msg: FIXMessage
    ):
        if FTag.ExecType in msg:
            if msg.get(FTag.ExecType) == "0":
                side = Side(int(msg[FTag.Side]))

                logging.debug(
                    "<--- [%s] %s: %s %s %s@%s"
                    % (
                        msg[FTag.MsgType],
                        msg[FTag.ClOrdID],
                        msg[FTag.Symbol],
                        side.name,
                        msg[FTag.OrderQty],
                        msg[FTag.Price],
                    )
                )
            elif msg.get(FTag.ExecType) == "0":
                reason = "Unknown" if FTag.Text not in msg else msg[FTag.Text]
                logging.info("Order Rejected '%s'" % (reason,))
        else:
            logging.error("Received execution report without ExecType")


if __name__ == "__main__":
    logging.basicConfig(
        level=logging.DEBUG,
        format="%(asctime)s [%(filename)20s:%(lineno)-4s] %(levelname)5s - %(message)s",
    )
    client = Client()
    asyncio.run(client.start("localhost", 9898))
