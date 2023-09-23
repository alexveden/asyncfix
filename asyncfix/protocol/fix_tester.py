from math import nan, isnan

from asyncfix import FIXMessage, FTag, FMsg

from .common import FExecType, FOrdStatus
from .order_single import FIXNewOrderSingle


class FIXTester:
    def __init__(self):
        self.registered_orders = {}

    def order_register_single(self, o: FIXNewOrderSingle):
        self.registered_orders[o.clord_id] = o
        return True

    def order_register_cxlrep(self, o: FIXNewOrderSingle, rep: FIXMessage):
        pass

    def fix_cxl_request(self, o: FIXNewOrderSingle) -> FIXMessage:
        pass

    def fix_rep_request(
        self, o: FIXNewOrderSingle, price: float = nan, qty: float = nan
    ) -> FIXMessage:
        pass

    def fix_cxlrep_reject_msg(
        self,
        cancel_msg: FIXMessage,
        ord_status: FOrdStatus,
    ) -> FIXMessage:
        pass

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

        if orig_clord_id:
            m[FTag.OrigClOrdID] = orig_clord_id
        m[FTag.ExecType] = exec_type
        m[FTag.OrdStatus] = ord_status

        if isnan(order_qty):
            order_qty = order.qty
        else:
            assert (
                exec_type == FExecType.REPLACED
            ), "Only applicable to exec_type=5 (replace)"
            assert order_qty > 0
        m[FTag.OrderQty] = order_qty

        if isnan(cum_qty):
            cum_qty = order.cum_qty
        else:
            assert cum_qty <= order.qty
            assert cum_qty >= 0
        m[FTag.CumQty] = 14

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
            m[FTag.Price] = price

        # if exec_type == FIX_ET_PCXL and ord_status == FIX_OS_PCXL:
        if (
            exec_type == FExecType.PENDING_CANCEL
            and ord_status == FOrdStatus.PENDING_CANCEL
        ):
            assert order.orig_clord_id > 0
            assert order.clord_id > 0
            assert order.clord_id > order.orig_clord_id
            assert order.cum_qty == cum_qty
            assert order.leaves_qty == leaves_qty

        if (
            ord_status == FOrdStatus.FILLED
            or ord_status == FOrdStatus.CANCELED
            or ord_status == FOrdStatus.REJECTED
            or ord_status == FOrdStatus.EXPIRED
        ):
            assert leaves_qty == 0, "New order report is finished, but LeavesQty != 0"

        return m
