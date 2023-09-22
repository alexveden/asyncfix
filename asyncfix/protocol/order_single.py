from datetime import datetime

from asyncfix import FIXMessage, FMsg, FTag

from .common import FExecType, FOrdSide, FOrdStatus, FOrdType


class FIXNewOrderSingle:
    def __init__(
        self,
        clord_id: str,
        cl_ticker: str,
        side: FOrdSide | str,
        price: float,
        qty: float,
        ord_type: FOrdType | str = FOrdType.LIMIT,
        account: str | dict = "000000",
        target_price: float | None = None,
    ):
        self.clord_id = clord_id
        self.orig_clord_id = None
        self.ticker = cl_ticker
        self.side = side
        self.price = price
        self.qty = qty
        self.leaves_qty = 0.0
        self.cum_qty = 0.0
        self.ord_type = ord_type
        self.account = account
        self.clord_id_cnt = 0
        self.status: FOrdStatus = FOrdStatus.CREATED
        self.target_price = target_price if target_price is not None else price

    def next_clord(self):
        self.clord_id_cnt += 1
        return f"{self.clord_id}-{self.clord_id_cnt}"

    @staticmethod
    def current_datetime():
        return datetime.utcnow().strftime("%Y%m%d-%H:%M:%S.%f")[:-3]

    def fix_new(self) -> FIXMessage:
        """
        Creates NewOrderSingle message
        """
        o = FIXMessage(FMsg.NEWORDERSINGLE)
        o[FTag.ClOrdID] = self.clord_id

        # setting instrument identification fields (may vary for different FIX brokers)
        self.set_instrument(o)

        # setting account field (may vary for different FIX brokers)
        self.set_account(o)
        o[FTag.Side] = self.side
        o[FTag.TransactTime] = self.current_datetime()

        # setting price and qty (typically tick size rounding, etc)
        self.set_price_qty(o, self.price, self.qty)

        return o

    def set_instrument(self, ord_msg: FIXMessage):
        """
        Set order instrument definition (override this in child)

        Args:
            ord_msg: new or replaced order

        """
        # Simply populate symbol, in read life FIX counterparty may require populate
        #  more fields (override this method in child class)
        ord_msg[FTag.Symbol] = self.ticker

    def set_account(self, ord_msg: FIXMessage):
        """
        Set account definition (override this in child)

        Args:
            ord_msg: new or replaced order

        """
        # Simplistic account setting (you must override this method in child class)
        assert isinstance(self.account, str), "Account expected a string"
        ord_msg[FTag.Account] = self.account

    def set_price_qty(self, ord_msg: FIXMessage, price: float, qty: float):
        """
        Set order price and qty definition (override this in child)

        This method handles custom price/qty rounding/decimal formatting, or maybe
        conditional presence of two fields based on order type

        Args:
            ord_msg: new or replaced order

        """
        ord_msg[FTag.Price] = price
        ord_msg[FTag.OrderQty] = qty

    @staticmethod
    def change_status(
        status: FOrdStatus,
        fix_msg_type: FMsg,
        msg_exec_type: FExecType,
        msg_status: FOrdStatus,
    ) -> int:
        pass

    def process_cancel_rej_report(self, m: FIXMessage) -> int:
        pass

    def process_execution_report(self, m: FIXMessage) -> int:
        pass

    def is_finished(self) -> bool:
        pass

    def can_cancel(self) -> bool:
        pass

    def can_replace(self) -> bool:
        pass

    def cancel_req(self) -> FIXMessage:
        pass

    def replace_req(self, price: float, qty: float) -> FIXMessage:
        pass
