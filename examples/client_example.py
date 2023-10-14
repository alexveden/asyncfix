"""Simple AsyncFIX client example."""
import asyncio
import logging

from asyncfix import AsyncFIXClient, ConnectionState, FIXMessage, FMsg, FTag, Journaler
from asyncfix.protocol import FIXNewOrderSingle, FIXProtocol44, FOrdSide, FOrdType


class Client(AsyncFIXClient):
    """Simple AsyncFIX client."""

    def __init__(self):
        """Initialize."""
        journal = Journaler("client_example.store")
        super().__init__(
            protocol=FIXProtocol44(),
            sender_comp_id="TCLIENT",
            target_comp_id="TSERVER",
            journaler=journal,
            host="localhost",
            port=9898,
        )
        self.orders: dict[str, FIXNewOrderSingle] = {}
        self.clord_id = 0

    async def on_connect(self):
        """(AppEvent) Underlying socket connected."""
        self.log.info("on_connect: sending logon")

        logon_msg = FIXMessage(
            FMsg.LOGON,
            {
                FTag.EncryptMethod: 0,
                FTag.HeartBtInt: self._heartbeat_period,
            },
        )
        await self.send_msg(logon_msg)

    async def on_disconnect(self):
        """(AppEvent) Underlying socket disconnected."""
        self.log.info("on_disconnect")

    async def on_logon(self, is_healthy: bool):
        """(AppEvent) Logon(35=A) received from peer.

        Args:
            is_healthy: True - if connection_state is ACTIVE
        """
        self.log.info("on_logon")

    async def on_logout(self, msg: FIXMessage):
        """(AppEvent) Logout(35=5) received from peer.

        Args:
            msg: Logout message
        """
        self.log.info("on_logout")

    async def should_replay(self, historical_replay_msg: FIXMessage) -> bool:
        """(AppLevel) Checks if historical_replay_msg from Journaler should be replayed.

        Args:
            historical_replay_msg: message from Journaler log

        Returns: True - replay, False - msg skipped (replaced by SequenceReset(35=4))
        """
        return True

    async def on_state_change(self, connection_state: ConnectionState):
        """(AppEvent) On ConnectionState change.

        Args:
            connection_state: new connection state
        """
        self.log.info("on_state_change")
        if connection_state == ConnectionState.ACTIVE:
            # Send test order once connected
            await self.send_order()

    async def on_message(self, msg: FIXMessage):
        """(AppEvent) Business message was received.

        Typically excludes session messages

        Args:
            msg: generic incoming message
        """
        if msg.msg_type == FMsg.EXECUTIONREPORT:
            await self.on_execution_report(msg)
        else:
            self.log.debug(f"on_message: app msg skipped: {msg}")

    async def send_order(self):
        """Sends test order."""
        self.clord_id = self.clord_id + 1
        order = FIXNewOrderSingle(
            f"test-order-{self.clord_id}",
            cl_ticker="MYTICKER",
            side=FOrdSide.BUY,
            price=199,
            qty=3,
            ord_type=FOrdType.MARKET,
            account="ABS21233",
        )
        self.log.debug(f"NewOrderSingle: {order}")

        # Generate NewOrderSingle FIXMessage
        msg = order.new_req()
        msg[FTag.AcctIDSource] = 12
        msg[21994] = "ExtraInfo"
        self.orders[order.clord_id] = order

        await self.send_msg(msg)

    async def on_execution_report(self, msg: FIXMessage):
        """Processes execution report."""
        clord_id = msg[FTag.ClOrdID]
        if clord_id in self.orders:
            order = self.orders[clord_id]

            order.process_execution_report(msg)

            self.log.info(f"ExecutionReport: {repr(order)}")

            if order.can_cancel():
                self.log.debug("cancelling order")
                cxl_req = order.cancel_req()
                await self.send_msg(cxl_req)
        else:
            self.log.log


async def main():
    """Main function."""
    client = Client()
    await client.connect()

    while True:
        await asyncio.sleep(0.1)


if __name__ == "__main__":
    logging.basicConfig(
        level=logging.DEBUG,
        format="%(asctime)s [%(filename)20s:%(lineno)-4s] %(levelname)5s - %(message)s",
    )
    asyncio.run(main())
