import asyncio
import logging

from asyncfix import (
    AsyncFIXDummyServer,
    ConnectionState,
    FIXMessage,
    FIXTester,
    FMsg,
    FTag,
    Journaler,
)
from asyncfix.protocol import FExecType, FIXNewOrderSingle, FIXProtocol44, FOrdStatus


class Server(AsyncFIXDummyServer):
    def __init__(self):
        journal = Journaler("server_example.store")
        super().__init__(
            protocol=FIXProtocol44(),
            sender_comp_id="TSERVER",
            target_comp_id="TCLIENT",
            journaler=journal,
            host="localhost",
            port=9898,
        )
        self.fix_tester = FIXTester()
        self.orders: dict[str, FIXNewOrderSingle] = {}
        self.clord_id = 0

    async def on_connect(self):
        """
        (AppEvent) Underlying socket connected

        """
        self.log.info("on_connect")

    async def on_disconnect(self):
        """
        (AppEvent) Underlying socket disconnected

        """
        self.log.info("on_disconnect")

    async def on_logon(self, is_healthy: bool):
        """
        (AppEvent) Logon(35=A) received from peer

        Args:
            is_healthy: True - if connection_state is ACTIVE
        """
        self.log.info("on_logon")

    async def on_logout(self, msg: FIXMessage):
        """
        (AppEvent) Logout(35=5) received from peer

        Args:
            msg:

        """
        self.log.info("on_logout")

    async def should_replay(self, historical_replay_msg: FIXMessage) -> bool:
        """
        (AppLevel) Checks if historical_replay_msg from Journaler should be replayed

        Args:
            historical_replay_msg: message from Journaler log

        Returns: True - replay, False - msg skipped (replaced by SequenceReset(35=4))

        """
        return True

    async def on_state_change(self, connection_state: ConnectionState):
        """
        (AppEvent) On ConnectionState change

        Args:
            connection_state: new connection state
        """
        self.log.info("on_state_change")

    async def on_message(self, msg: FIXMessage):
        """
        (AppEvent) Business message was received

        Typically excludes session messages

        Args:
            msg:

        """
        if msg.msg_type == FMsg.NEWORDERSINGLE:
            await self.on_new_order(msg)
        else:
            self.log.debug(f"on_message: app msg skipped: {msg}")

    async def on_new_order(self, msg: FIXMessage):
        """
        Reply execution report on incoming order request

        Args:
            msg:

        """
        try:
            msg = FIXMessage(
                FMsg.EXECUTIONREPORT,
                {
                    FTag.Price: msg.get(FTag.Price, 0),
                    FTag.Symbol: msg.get(FTag.Symbol),
                    FTag.Account: msg[1],  # tag=1 (not index!)
                    FTag.OrdStatus: FOrdStatus.NEW,
                    FTag.ExecType: FExecType.NEW,
                    FTag.Side: msg.get(FTag.Side),
                    FTag.ClOrdID: msg.get(FTag.ClOrdID),
                    FTag.OrderQty: msg[FTag.OrderQty],
                    FTag.OrderID: 77,
                    FTag.LeavesQty: "10",
                    FTag.CumQty: "0",
                    FTag.AvgPx: "0",
                },
            )
            await self.send_msg(msg)

        except Exception as e:
            msg = FIXMessage(FMsg.EXECUTIONREPORT)
            msg.set(FTag.OrdStatus, FOrdStatus.REJECTED)
            msg.set(FTag.ExecType, FExecType.REJECTED)
            msg.set(FTag.LeavesQty, "0")
            msg.set(FTag.Text, str(e))
            msg.set(FTag.ClOrdID, msg.get(FTag.ClOrdID))
            await self.send_msg(msg)


async def main():
    server = Server()

    # Works forever
    await server.connect()


if __name__ == "__main__":
    logging.basicConfig(
        level=logging.DEBUG,
        format="%(asctime)s [%(filename)20s:%(lineno)-4s] %(levelname)5s - %(message)s",
    )
    asyncio.run(main())
