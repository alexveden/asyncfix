from math import nan

from asyncfix import FIXMessage

from .common import FExecType, FOrdStatus
from .order_single import FIXNewOrderSingle


class FIXTester:
    def order_register_single(self, o: FIXNewOrderSingle):
        pass

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
        pass
