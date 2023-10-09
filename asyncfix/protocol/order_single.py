import re
from datetime import datetime
from math import isfinite, nan

from asyncfix import FIXMessage, FMsg, FTag
from asyncfix.errors import FIXError

from .common import FExecType, FOrdSide, FOrdStatus, FOrdType

RE_CLORD_ROOT = re.compile(r"^(.+)--(\d+)$", re.MULTILINE)


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
        assert clord_id, "empty clord_id"

        self.clord_id = clord_id
        self.orig_clord_id = None
        self.order_id = None
        self.ticker = cl_ticker
        self.side = side
        self.price = price
        self.qty = qty
        self.leaves_qty = 0.0
        self.cum_qty = 0.0
        self.avg_px = nan
        self.ord_type = ord_type
        self.account = account
        self.clord_id_cnt = 0
        self.status: FOrdStatus = FOrdStatus.CREATED
        self.target_price = target_price if target_price is not None else price

    def __repr__(self):
        return (
            f"FIXNewOrderSingle({self.status.name}, clord={self.clord_id},"
            f" ticker={self.ticker}, px={self.price}, qty={self.qty},"
            f" leavesqty={self.leaves_qty}, cumqty={self.cum_qty})"
        )

    def clord_next(self) -> str:
        """
        New ClOrdID for current order management
        """
        self.clord_id_cnt += 1
        return f"{self.clord_id_root}--{self.clord_id_cnt}"

    @staticmethod
    def clord_root(clord_id: str) -> str:
        match = RE_CLORD_ROOT.match(clord_id)
        if match:
            return match[1]
        else:
            return clord_id

    @property
    def clord_id_root(self) -> str:
        return self.clord_root(self.clord_id)

    @staticmethod
    def current_datetime():
        """
        TransactTime field
        """
        return datetime.utcnow().strftime("%Y%m%d-%H:%M:%S.%f")[:-3]

    def new_req(self) -> FIXMessage:
        """
        Creates NewOrderSingle message
        """
        assert (
            self.status == FOrdStatus.CREATED
        ), "new_req() must send only just created orders"

        o = FIXMessage(FMsg.NEWORDERSINGLE)
        self.clord_id = self.clord_next()
        o[FTag.ClOrdID] = self.clord_id

        # setting instrument identification fields (may vary for different FIX brokers)
        self.set_instrument(o)

        # setting account field (may vary for different FIX brokers)
        self.set_account(o)
        o[FTag.OrdType] = self.ord_type
        o[FTag.Side] = self.side
        o[FTag.TransactTime] = self.current_datetime()

        # setting price and qty (typically tick size rounding, etc)
        self.set_price_qty(o, self.price, self.qty)

        self.status = FOrdStatus.PENDING_NEW

        return o

    def cancel_req(self) -> FIXMessage:
        """
        Creates order cancel request

        Raises:
            FIXError: if order can't be canceled

        """
        if not self.can_cancel():
            raise FIXError(f"{self} Fix order is not allowed for cancel")

        assert not self.orig_clord_id
        self.orig_clord_id = self.clord_id
        self.clord_id = self.clord_next()

        cxl_req_msg = FIXMessage(FMsg.ORDERCANCELREQUEST)
        cxl_req_msg[11] = self.clord_id
        cxl_req_msg[38] = self.qty
        cxl_req_msg[41] = self.orig_clord_id
        self.set_instrument(cxl_req_msg)
        cxl_req_msg[FTag.Side] = self.side
        cxl_req_msg[FTag.TransactTime] = self.current_datetime()

        self.status = FOrdStatus.PENDING_CANCEL

        return cxl_req_msg

    def replace_req(self, price: float = nan, qty: float = nan) -> FIXMessage:
        """
        Creates order replace request

        Args:
            price: alternative price
            qty: alternative qty

        Returns:
            message

        Raises:
            FIXError: if order can't be replaced or price/qty unchanged

        """
        if not self.can_replace():
            raise FIXError("Order cannot be replaced")

        if price is None or not isfinite(price) or price == self.price:
            price = self.price
        if qty is None or not isfinite(qty) or qty == self.qty or qty == 0:
            qty = self.qty

        if price == self.price and qty == self.qty:
            raise FIXError("no price / qty change in replace_req")

        assert not self.orig_clord_id
        self.orig_clord_id = self.clord_id
        self.clord_id = self.clord_next()

        m = FIXMessage(FMsg.ORDERCANCELREPLACEREQUEST)
        m[FTag.ClOrdID] = self.clord_id
        m[FTag.OrigClOrdID] = self.orig_clord_id
        m[FTag.OrdType] = self.ord_type
        self.set_instrument(m)
        self.set_price_qty(m, price, qty)
        m[FTag.Side] = self.side
        m[FTag.TransactTime] = self.current_datetime()

        self.status = FOrdStatus.PENDING_REPLACE

        return m

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
        raise_on_err: bool = True,
    ) -> FOrdStatus | None:
        """
        FIX Order State transition algo

        :param status: current order status
        :param fix_msg_type: incoming/or requesting order type,  these are supported:
                '8' - execution report,
                '9' - Order Cancel reject,
                'F' - Order cancel request (if possible to cancel current order)
                'G' -  Order replace request (if possible to replace current order)
        :param msg_exec_type: (only for execution report), for other should be 0
        :param msg_status: new fix msg order status, or required status
        :return: FOrdStatus if state transition is possible,
                 None - if transition is valid, but need to wait for a good state
                 raises FIXError - when transition is invalid
        """
        status_transitions = {}

        if fix_msg_type == FMsg.EXECUTIONREPORT:
            status_transitions = {
                None: {None: FIXError},
                # key {initial status}: {
                #    msg_status: <transition>,
                #       <transition>: None - ignore, True - transit, FIXError - raise
                #
                #      REJECTED: True,     #  this is allowed status transition
                #      PENDING_NEW: None,  #  transition allowed but no status change
                #      CREATED: FIXError,  #  error transition
                #      None:  [None, True, FIXError] # default transition
                #  }
                FOrdStatus.CREATED: {
                    FOrdStatus.PENDING_NEW: True,
                    FOrdStatus.REJECTED: True,
                    None: FIXError,
                },
                FOrdStatus.PENDING_NEW: {
                    FOrdStatus.REJECTED: True,
                    FOrdStatus.NEW: True,
                    FOrdStatus.FILLED: True,
                    FOrdStatus.PARTIALLY_FILLED: True,
                    FOrdStatus.CANCELED: True,
                    FOrdStatus.SUSPENDED: True,
                    None: FIXError,
                },
                FOrdStatus.NEW: {
                    FOrdStatus.NEW: None,
                    FOrdStatus.PENDING_NEW: FIXError,
                    FOrdStatus.CREATED: FIXError,
                    FOrdStatus.ACCEPTED_FOR_BIDDING: FIXError,
                    None: True,
                },
                FOrdStatus.FILLED: {
                    None: None,
                },
                FOrdStatus.CANCELED: {
                    None: None,
                },
                FOrdStatus.REJECTED: {
                    None: None,
                },
                FOrdStatus.EXPIRED: {
                    None: None,
                },
                FOrdStatus.SUSPENDED: {
                    FOrdStatus.NEW: True,
                    FOrdStatus.PARTIALLY_FILLED: True,
                    FOrdStatus.CANCELED: True,
                    FOrdStatus.SUSPENDED: None,
                    None: FIXError,
                },
                FOrdStatus.PARTIALLY_FILLED: {
                    FOrdStatus.FILLED: True,
                    FOrdStatus.PARTIALLY_FILLED: True,
                    FOrdStatus.PENDING_REPLACE: True,
                    FOrdStatus.PENDING_CANCEL: True,
                    FOrdStatus.CANCELED: True,
                    FOrdStatus.EXPIRED: True,
                    FOrdStatus.SUSPENDED: True,
                    FOrdStatus.STOPPED: True,
                    None: FIXError,
                },
                FOrdStatus.PENDING_CANCEL: {
                    FOrdStatus.CANCELED: True,
                    FOrdStatus.CREATED: FIXError,
                    None: None,
                },
                FOrdStatus.PENDING_REPLACE: {
                    "exec_type": {
                        FExecType.REPLACED: {
                            FOrdStatus.NEW: True,
                            FOrdStatus.PARTIALLY_FILLED: True,
                            FOrdStatus.FILLED: True,
                            FOrdStatus.CANCELED: True,
                            None: FIXError,
                        },
                        None: {
                            FOrdStatus.CREATED: FIXError,
                            FOrdStatus.ACCEPTED_FOR_BIDDING: FIXError,
                            None: None,
                        },
                    },
                },
            }

        elif fix_msg_type == FMsg.ORDERCANCELREJECT:  # '9'
            status_transitions = {
                None: {
                    FOrdStatus.CREATED: FIXError,
                    FOrdStatus.ACCEPTED_FOR_BIDDING: FIXError,
                    None: True,
                }
            }
        elif (
            fix_msg_type == FMsg.ORDERCANCELREQUEST
            or fix_msg_type == FMsg.ORDERCANCELREPLACEREQUEST
        ):
            status_transitions = {
                FOrdStatus.PENDING_CANCEL: {None: None},
                FOrdStatus.PENDING_REPLACE: {None: None},
                FOrdStatus.NEW: {None: True},
                FOrdStatus.SUSPENDED: {None: True},
                FOrdStatus.PARTIALLY_FILLED: {None: True},
                None: {None: FIXError},
            }

        if not status_transitions:
            raise FIXError(f"No status transition table for {fix_msg_type=}")

        s = status_transitions.get(status, status_transitions[None])
        if isinstance(s, dict) and "exec_type" in s:
            s = s["exec_type"].get(msg_exec_type, s["exec_type"][None])
        default = s[None]
        result = s.get(msg_status, default)

        if result is FIXError:
            # Invalid transition
            if raise_on_err:
                raise FIXError("FIX Order state transition error")
            else:
                return None
        else:
            if result is None:
                # Valid transition no status change
                return None
            else:
                # Do status change
                return msg_status

    def process_cancel_rej_report(self, m: FIXMessage) -> bool:
        """
        Processes incoming cancel reject report message
        """
        if m.msg_type != FMsg.ORDERCANCELREJECT:
            raise FIXError("incorrect message type")

        order_status = m[FTag.OrdStatus]

        new_status = self.change_status(
            self.status, m.msg_type, 0, order_status, raise_on_err=False
        )
        #
        if order_status == FOrdStatus.REJECTED:
            # Very weird (emergency) case, because the ClOrdId does not exist
            #   Let's set order inactive
            self.leaves_qty = 0

        if new_status is not None:
            self.status = new_status
            return True
        else:
            return False

    def process_execution_report(self, m: FIXMessage) -> bool:
        """
        Processes incoming execution report for an order

        Raises:
            FIXError: if ClOrdID mismatch
        """
        if m.msg_type != FMsg.EXECUTIONREPORT:
            raise FIXError("incorrect message type")

        clord_id = m[FTag.ClOrdID]
        cum_qty = float(m[FTag.CumQty])
        order_status = m[FTag.OrdStatus]

        if clord_id != self.clord_id and clord_id != self.orig_clord_id:
            raise FIXError("orig_clord_id mismatch")

        exec_type = m[FTag.ExecType]
        leaves_qty = float(m[FTag.LeavesQty])

        new_status = FIXNewOrderSingle.change_status(
            self.status, m.msg_type, exec_type, order_status, raise_on_err=False
        )

        self.order_id = m[FTag.OrderID]
        self.leaves_qty = leaves_qty
        self.cum_qty = cum_qty
        self.avg_px = float(m[FTag.AvgPx])

        if exec_type == FExecType.REPLACED:
            # Order has been successfully replaced
            new_price = m.get(FTag.Price, None)
            if new_price is not None:
                # Price may not be in execution report, it's not an error
                self.price = float(new_price)

            order_qty = m.get(FTag.OrderQty, None)
            if order_qty is not None:
                # Qty may not be in execution report, it's not an error
                self.qty = float(order_qty)

            # Clearing OrigOrdId to allow subsequent order changes
            self.orig_clord_id = None

        if new_status:
            self.status = FOrdStatus(new_status)
            return True
        else:
            return False

    def is_finished(self) -> bool:
        """
        Check if order is in terminal state (no subsequent changes expected)
        """
        return (
            self.status == FOrdStatus.FILLED
            or self.status == FOrdStatus.CANCELED
            or self.status == FOrdStatus.REJECTED
            or self.status == FOrdStatus.EXPIRED
        )

    def can_cancel(self) -> bool:
        """
        Check if order can be canceled from its current state
        """
        return (
            FIXNewOrderSingle.change_status(
                self.status,
                FMsg.ORDERCANCELREQUEST,
                0,  # Exec Type - omitted!
                FOrdStatus.PENDING_CANCEL,
                raise_on_err=False,
            )
            is not None
        )

    def can_replace(self) -> bool:
        """
        Check if order can be replaced from its current state
        """
        return (
            FIXNewOrderSingle.change_status(
                self.status,
                FMsg.ORDERCANCELREPLACEREQUEST,
                0,  # Exec Type - omitted!
                FOrdStatus.PENDING_REPLACE,
                raise_on_err=False,
            )
            is not None
        )
