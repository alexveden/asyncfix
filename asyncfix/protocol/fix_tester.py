from math import isnan, nan

from asyncfix import FIXMessage, FMsg, FTag

from .common import FExecType, FOrdStatus
from .order_single import FIXNewOrderSingle
from .schema import FIXSchema
from asyncfix.session import FIXSession
from asyncfix.connection import AsyncFIXConnection
from unittest.mock import MagicMock, AsyncMock


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
        self.connection = connection
        self.connection_session = None
        self.msent: list[FIXMessage] = []
        """list of fix messages sent by self.connection.send_msg()"""

        if connection:
            assert isinstance(connection, AsyncFIXConnection)
            # target and session swapped! Because we mimic the server
            self.connection_session = FIXSession(
                "fix_tester",
                target_comp_id=self.connection.session.sender_comp_id,
                sender_comp_id=self.connection.session.target_comp_id,
            )
            self.connection_session.snd_seq_num = (
                connection.session.next_expected_msg_seq_num - 1
            )
            self.connection_session.next_expected_msg_seq_num = (
                connection.session.snd_seq_num + 1
            )
            connection.socket_writer = MagicMock()
            connection.socket_writer.write.side_effect = self._connection_socket_write
            connection.socket_writer.drain = AsyncMock()

    def msent_count(self):
        return len(self.msent)

    def msent_reset(self):
        self.msent.clear()

    def msent_query(
        self,
        tags: tuple[FTag | str | int] | None = None,
        index: int = -1,
    ) -> dict[FTag | str, str]:
        return self.msent[index].query(*tags)

    def _connection_socket_write(self, data):
        msg, _, _ = self.connection.codec.decode(data, silent=False)
        if self.schema:
            self.schema.validate(msg)
        self.connection_next_sn = int(msg[FTag.MsgSeqNum]) + 1
        self.msent.append(msg)

    async def reply(self, msg: FIXMessage):
        if self.schema:
            self.schema.validate(msg)

        raw_msg = self.connection.codec.encode(
            msg,
            self.connection_session,
            raw_seq_num=FTag.MsgSeqNum in msg,
        ).encode()

        decoded_msg, _, _ = self.connection.codec.decode(raw_msg, silent=False)

        await self.connection._process_message(decoded_msg, raw_msg)

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
