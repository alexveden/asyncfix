from math import isnan, nan
import asyncio

from asyncfix.journaler import Journaler
from asyncfix import FIXMessage, FMsg, FTag
from asyncfix.protocol import FIXSchema, FIXProtocol44

from .common import FExecType, FOrdStatus
from .order_single import FIXNewOrderSingle
from .schema import FIXSchema
from asyncfix.session import FIXSession
from asyncfix.connection import AsyncFIXConnection
from unittest.mock import MagicMock, AsyncMock
from asyncfix.connection import AsyncFIXConnection, ConnectionState, ConnectionRole


class FIXTester:
    def __init__(
        self,
        schema: FIXSchema | None = None,
        connection: AsyncFIXConnection | None = None,
    ):
        self.registered_orders = {}
        self.schema = schema
        self.order_id = 0
        self.exec_id = 10000
        self.conn_init = connection
        self.conn_accept = None
        self.msg_out: list[FIXMessage] = []
        """list of fix messages sent by self.connection.send_msg()"""
        self.msg_out_que: list[tuple(FIXMessage, bytes)] = []

        self.msg_in: list[FIXMessage] = []
        """list of fix messages sent by FIXTester.reply()"""

        if connection:
            assert isinstance(connection, AsyncFIXConnection)
            # target and session swapped! Because we mimic the server
            j = Journaler()
            self.conn_accept = AsyncFIXConnection(
                FIXProtocol44(),
                target_comp_id=self.conn_init.session.sender_comp_id,
                sender_comp_id=self.conn_init.session.target_comp_id,
                journaler=j,
                host="localhost",
                port="64444",
                heartbeat_period=30,
                start_tasks=False,
            )
            self.conn_accept.connection_state = ConnectionState.NETWORK_CONN_ESTABLISHED
            self.conn_accept.session.next_num_out = connection.session.next_num_in
            self.conn_accept.session.next_num_in = connection.session.next_num_out

            connection.socket_writer = MagicMock()
            connection.socket_writer.write.side_effect = self._conn_socket_write_out
            connection.socket_writer.drain = AsyncMock()
            connection.socket_writer.wait_closed = AsyncMock()

            self.conn_accept.socket_writer = MagicMock()
            self.conn_accept.socket_writer.write.side_effect = (
                self._conn_socket_write_in
            )
            self.conn_accept.socket_writer.drain = AsyncMock()
            self.conn_accept.socket_writer.drain.side_effect = (
                self._conn_socket_drain_in
            )
            self._socket_drain_in_coro = None
            self.conn_accept.socket_writer.wait_closed = AsyncMock()

    def set_next_num(self, num_in=None, num_out=None):
        if num_in is not None:
            assert isinstance(num_in, int)
            assert num_in > 0
            self.conn_accept.session.next_num_in = num_in
        if num_out is not None:
            assert isinstance(num_out, int)
            assert num_out > 0
            self.conn_accept.session.next_num_out = num_out

    def msg_out_count(self):
        return len(self.msg_out)

    def msg_in_count(self):
        return len(self.msg_out)

    def msg_reset(self):
        self.msg_out.clear()
        self.msg_out_que.clear()
        self.msg_in.clear()

    def msg_in_query(
        self,
        tags: tuple[FTag | str | int] | None = None,
        index: int = -1,
    ) -> dict[FTag | str, str]:
        """
        Query message sent from FIXTester to initiator
        Args:
            tags:
            index:

        Returns:


        """
        return self.msg_in[index].query(*tags)

    def msg_out_query(
        self,
        tags: tuple[FTag | str | int] | None = None,
        index: int = -1,
    ) -> dict[FTag | str, str]:
        """
        Query message sent from initiator to FixTester

        Args:
            tags:
            index:

        Returns:


        """
        return self.msg_out[index].query(*tags)

    def _conn_socket_write_out(self, data):
        msg, _, _ = self.conn_init.codec.decode(data, silent=False)
        if self.schema:
            self.schema.validate(msg)
        self.msg_out.append(msg)
        self.msg_out_que.append((msg, data))

    def _conn_socket_write_in(self, data):
        msg, _, _ = self.conn_accept.codec.decode(data, silent=False)
        if self.schema:
            self.schema.validate(msg)
        self.msg_in.append(msg)

        self._socket_drain_in_coro = self.conn_init._process_message(msg, data)

    async def _conn_socket_drain_in(self):
        try:
            if self._socket_drain_in_coro:
                await self._socket_drain_in_coro
        finally:
            self._socket_drain_in_coro = None

    async def process_msg_acceptor(self, index=-1):
        assert len(self.msg_out), "no incoming messages registered"
        await self.conn_accept._process_message(
            self.msg_out_que[index][0], self.msg_out_que[index][1]
        )

    async def reply(self, msg: FIXMessage):
        if self.schema:
            self.schema.validate(msg)

        raw_msg = self.conn_accept.codec.encode(
            msg,
            self.conn_accept.session,
            raw_seq_num=FTag.MsgSeqNum in msg,
        ).encode()

        # Pretend the message was transfered to initiator
        decoded_msg, _, _ = self.conn_init.codec.decode(raw_msg, silent=False)

        if self.schema:
            self.schema.validate(decoded_msg)

        await self.conn_init._process_message(decoded_msg, raw_msg)

        return decoded_msg

    def next_order_id(self) -> int:
        self.order_id += 1
        return self.order_id

    def next_exec_id(self) -> int:
        self.exec_id += 1
        return self.exec_id

    def order_register_single(self, o: FIXNewOrderSingle):
        self.registered_orders[o.clord_id] = o
        return True

    def fix_cxl_request(self, o: FIXNewOrderSingle) -> FIXMessage:
        m = o.cancel_req()
        if self.schema:
            self.schema.validate(m)
        assert o.can_cancel()  # new assert 2023-09-23
        o.status = FOrdStatus.PENDING_CANCEL
        self.registered_orders[o.clord_id] = o
        return m

    def fix_rep_request(
        self, o: FIXNewOrderSingle, price: float = nan, qty: float = nan
    ) -> FIXMessage:
        m = o.replace_req(price, qty)
        if self.schema:
            self.schema.validate(m)
        assert o.can_replace()
        o.status = FOrdStatus.PENDING_REPLACE
        self.registered_orders[o.clord_id] = o
        return m

    def fix_cxlrep_reject_msg(
        self,
        cxl_req: FIXMessage,
        ord_status: FOrdStatus,
    ) -> FIXMessage:
        clord_id = cxl_req[FTag.ClOrdID]
        orig_clord_id = cxl_req[FTag.OrigClOrdID]

        m = FIXMessage(FMsg.ORDERCANCELREJECT)
        m[37] = 0
        m[11] = clord_id
        m[41] = orig_clord_id
        m[39] = ord_status

        assert cxl_req.msg_type in [
            FMsg.ORDERCANCELREQUEST,
            FMsg.ORDERCANCELREPLACEREQUEST,
        ]

        if cxl_req.msg_type == FMsg.ORDERCANCELREQUEST:
            m[FTag.CxlRejResponseTo] = "1"
        elif cxl_req.msg_type == FMsg.ORDERCANCELREPLACEREQUEST:
            m[FTag.CxlRejResponseTo] = "2"

        if self.schema:
            self.schema.validate(m)

        return m

    def fix_exec_report_msg(
        self,
        order: FIXNewOrderSingle,
        clord_id: str,
        exec_type: FExecType,
        ord_status: FOrdStatus,
        cum_qty: float = nan,
        leaves_qty: float = nan,
        last_qty: float = nan,
        price: float = nan,
        order_qty: float = nan,
        orig_clord_id: str = None,
    ) -> FIXMessage:
        assert order.clord_id in self.registered_orders, "Unregistered order!"

        m = FIXMessage(FMsg.EXECUTIONREPORT)
        assert clord_id
        m[FTag.ClOrdID] = clord_id

        if order.order_id is None:
            order_id = self.next_order_id()
        else:
            order_id = order.order_id

        m[FTag.OrderID] = order_id
        m[FTag.ExecID] = self.next_exec_id()

        if orig_clord_id:
            m[FTag.OrigClOrdID] = orig_clord_id
        m[FTag.ExecType] = exec_type
        m[FTag.OrdStatus] = ord_status
        m[FTag.Side] = order.side

        if isnan(order_qty):
            order_qty = order.qty
        else:
            assert (
                exec_type == FExecType.REPLACED
            ), "Only applicable to exec_type=5 (replace)"
            assert order_qty > 0

        if isnan(cum_qty):
            cum_qty = order.cum_qty
        else:
            assert cum_qty <= order.qty
            assert cum_qty >= 0
        m[FTag.CumQty] = cum_qty

        if isnan(leaves_qty):
            leaves_qty = order.leaves_qty
        else:
            assert leaves_qty >= 0
            assert leaves_qty <= order_qty

        m[FTag.LeavesQty] = leaves_qty
        assert (
            cum_qty + leaves_qty <= order_qty
        ), f"cum_qty[{cum_qty}] + leaves_qty[{leaves_qty}] <= order_qty[{order_qty}]"

        if not isnan(last_qty):
            assert not isnan(leaves_qty), "Must also set leaves_qty, when trade"
            assert not isnan(cum_qty), "Must also set cum_qty, when trade"
            assert (
                exec_type == FExecType.TRADE
            ), "Only applicable to exec_type=F (trade)"
            assert last_qty > 0
            m[FTag.LastQty] = last_qty
            assert (
                round(last_qty - (cum_qty - order.cum_qty), 3) == 0
            ), "Probably incorrect Trade qty"
        else:
            assert (
                exec_type != FExecType.TRADE
            ), "You must set last_qty when exec_type=F (trade)"

        if not isnan(price):
            assert (
                exec_type == FExecType.REPLACED
            ), "Only applicable to exec_type=5 (replace)"
        else:
            price = order.price

        order.set_instrument(m)

        order.set_price_qty(m, price, order_qty)
        m[FTag.AvgPx] = price

        order.set_account(m)

        if (
            exec_type == FExecType.PENDING_CANCEL
            and ord_status == FOrdStatus.PENDING_CANCEL
        ):
            assert order.orig_clord_id
            assert order.clord_id
            assert order.clord_id != order.orig_clord_id
            assert order.cum_qty == cum_qty
            assert order.leaves_qty == leaves_qty

        if (
            ord_status == FOrdStatus.FILLED
            or ord_status == FOrdStatus.CANCELED
            or ord_status == FOrdStatus.REJECTED
            or ord_status == FOrdStatus.EXPIRED
        ):
            assert leaves_qty == 0, "New order report is finished, but LeavesQty != 0"

        if self.schema:
            self.schema.validate(m)
        return m
