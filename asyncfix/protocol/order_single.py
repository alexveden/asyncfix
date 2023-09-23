from datetime import datetime
from math import isnan

from asyncfix import FIXMessage, FMsg, FTag
from asyncfix.errors import FIXError

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
        self.order_id = None
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

    def next_clord(self) -> str:
        self.clord_id_cnt += 1
        return f"{self.clord_id}-{self.clord_id_cnt}"

    @staticmethod
    def current_datetime():
        return datetime.utcnow().strftime("%Y%m%d-%H:%M:%S.%f")[:-3]

    def new_req(self) -> FIXMessage:
        """
        Creates NewOrderSingle message
        """
        o = FIXMessage(FMsg.NEWORDERSINGLE)
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
        if fix_msg_type == "8":  # Execution report
            if status == FOrdStatus.CREATED:
                # CREATED -> (PendingNew, Rejected)
                if msg_status == FOrdStatus.PENDING_NEW:
                    return FOrdStatus.PENDING_NEW
                elif msg_status == FOrdStatus.REJECTED:
                    return FOrdStatus.REJECTED
                else:
                    if raise_on_err:
                        raise FIXError("FIX Order state transition error")
                    else:
                        return None
            elif status == FOrdStatus.PENDING_NEW:
                # PendingNew -> (Rejected, New, Filled, Canceled)
                if msg_status == FOrdStatus.REJECTED:
                    return FOrdStatus.REJECTED
                elif msg_status == FOrdStatus.NEW:
                    return FOrdStatus.NEW
                elif msg_status == FOrdStatus.FILLED:
                    return FOrdStatus.FILLED
                elif msg_status == FOrdStatus.PARTIALLY_FILLED:
                    return FOrdStatus.PARTIALLY_FILLED
                elif msg_status == FOrdStatus.CANCELED:
                    return FOrdStatus.CANCELED
                elif msg_status == FOrdStatus.SUSPENDED:
                    return FOrdStatus.SUSPENDED
                else:
                    if raise_on_err:
                        raise FIXError("FIX Order state transition error")
                    else:
                        return None
            elif status == FOrdStatus.NEW:
                # New -> (Rejected, New, Suspended, PartiallyFilled, Filled,
                #         Canceled, Expired, DFD)
                if (
                    msg_status == FOrdStatus.PENDING_NEW
                    or msg_status == FOrdStatus.CREATED
                    or msg_status == FOrdStatus.ACCEPTED_FOR_BIDDING
                ):
                    if raise_on_err:
                        raise FIXError("FIX Order state transition error")
                    else:
                        return None
                elif msg_status == FOrdStatus.NEW:
                    # Reinstatement, allowed but not trigger state change
                    return None
                return msg_status
            elif (
                status == FOrdStatus.FILLED
                or status == FOrdStatus.CANCELED
                or status == FOrdStatus.REJECTED
                or status == FOrdStatus.EXPIRED
            ):
                # Order in terminal state - no status change allowed!
                return None
            elif status == FOrdStatus.SUSPENDED:
                # Order algorithmically was suspended
                if msg_status == FOrdStatus.NEW:
                    return FOrdStatus.NEW
                elif msg_status == FOrdStatus.PARTIALLY_FILLED:
                    return FOrdStatus.PARTIALLY_FILLED
                elif msg_status == FOrdStatus.CANCELED:
                    return FOrdStatus.CANCELED
                elif msg_status == FOrdStatus.SUSPENDED:
                    # Possible duplidates or delayed fills
                    return None
                else:
                    if raise_on_err:
                        raise FIXError("FIX Order state transition error")
                    else:
                        return None
            elif status == FOrdStatus.PARTIALLY_FILLED:
                if msg_status == FOrdStatus.FILLED:
                    return FOrdStatus.FILLED
                elif msg_status == FOrdStatus.PARTIALLY_FILLED:
                    return FOrdStatus.PARTIALLY_FILLED
                elif msg_status == FOrdStatus.PENDING_REPLACE:
                    return FOrdStatus.PENDING_REPLACE
                elif msg_status == FOrdStatus.PENDING_CANCEL:
                    return FOrdStatus.PENDING_CANCEL
                elif msg_status == FOrdStatus.CANCELED:
                    return FOrdStatus.CANCELED
                elif msg_status == FOrdStatus.EXPIRED:
                    return FOrdStatus.EXPIRED
                elif msg_status == FOrdStatus.SUSPENDED:
                    return FOrdStatus.SUSPENDED
                elif msg_status == FOrdStatus.STOPPED:
                    return FOrdStatus.STOPPED
                else:
                    if raise_on_err:
                        raise FIXError("FIX Order state transition error")
                    else:
                        return None
            elif status == FOrdStatus.PENDING_CANCEL:
                if msg_status == FOrdStatus.CANCELED:
                    return FOrdStatus.CANCELED
                elif msg_status == FOrdStatus.CREATED:
                    if raise_on_err:
                        raise FIXError("FIX Order state transition error")
                    else:
                        return None
                else:
                    return None
            elif status == FOrdStatus.PENDING_REPLACE:
                if msg_exec_type == FExecType.REPLACED:
                    # Successfully replaced
                    if (
                        msg_status == FOrdStatus.NEW
                        or msg_status == FOrdStatus.PARTIALLY_FILLED
                        or msg_status == FOrdStatus.FILLED
                        or msg_status == FOrdStatus.CANCELED
                    ):
                        return msg_status
                    else:
                        if raise_on_err:
                            raise FIXError("FIX Order state transition error")
                        else:
                            return None
                else:
                    if (
                        msg_status == FOrdStatus.CREATED
                        or msg_status == FOrdStatus.ACCEPTED_FOR_BIDDING
                    ):
                        if raise_on_err:
                            raise FIXError("FIX Order state transition error")
                        else:
                            return None
                    else:
                        # Technically does not count any status,
                        # until get replace reject or exec_type = FExecType.REPLACED
                        return None

            else:
                if raise_on_err:
                    raise FIXError("FIX Order state transition error")
                else:
                    return None

        elif fix_msg_type == "9":  # Order Cancel reject
            if (
                msg_status == FOrdStatus.CREATED
                or msg_status == FOrdStatus.ACCEPTED_FOR_BIDDING
            ):
                if raise_on_err:
                    raise FIXError("FIX Order state transition error")
                else:
                    return None
            return msg_status
        elif fix_msg_type == "F" or fix_msg_type == "G":
            # 'F' - Order cancel request (order requests self cancel)
            # 'G' -  Order replace request (order requests self change)
            if (
                status == FOrdStatus.PENDING_CANCEL
                or status == FOrdStatus.PENDING_REPLACE
            ):
                # Status is pending, we must wait
                return None
            elif (
                status == FOrdStatus.NEW
                or status == FOrdStatus.SUSPENDED
                or status == FOrdStatus.PARTIALLY_FILLED
            ):
                # Order is active and good for cancel/replacement
                return status
            else:
                if raise_on_err:
                    raise FIXError("FIX Order state transition error")
                else:
                    return None
        else:
            if raise_on_err:
                raise FIXError("FIX Order state transition error")
            else:
                return None

    def process_cancel_rej_report(self, m: FIXMessage) -> int:
        if m.msg_type != FMsg.ORDERCANCELREJECT:
            return -3  # DEF ERR_FIX_VALUE_ERROR        = -3

        order_status = m[FTag.OrdStatus]

        new_status = self.change_status(self.status, m.msg_type, 0, order_status)
        #
        if order_status == FOrdStatus.REJECTED:
            # Very weird (emergency) case, because the ClOrdId does not exist
            #   Let's set order inactive
            self.leaves_qty = 0

        if new_status is not None:
            self.status = new_status
            return 1
        else:
            return 0

    def process_execution_report(self, m: FIXMessage) -> int:
        assert m.msg_type == FMsg.EXECUTIONREPORT, "unexpected msg type"

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

        self.leaves_qty = leaves_qty
        self.cum_qty = cum_qty

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
            self.status = new_status
            return 1
        else:
            return 0

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
                self.status, "F", 0, FOrdStatus.PENDING_CANCEL, raise_on_err=False
            )
            is not None
        )

    def can_replace(self) -> bool:
        """
        Check if order can be replaced from its current state
        """
        return (
            FIXNewOrderSingle.change_status(
                self.status, "G", 0, FOrdStatus.PENDING_REPLACE, raise_on_err=False
            )
            is not None
        )

    def cancel_req(self) -> FIXMessage:
        if not self.can_cancel():
            raise FIXError(f"{self} Fix order is not allowed for cancel")

        assert not self.orig_clord_id
        self.orig_clord_id = self.clord_id
        self.clord_id = self.next_clord()

        cxl_req_msg = FIXMessage(FMsg.ORDERCANCELREQUEST)
        cxl_req_msg[11] = self.clord_id
        cxl_req_msg[38] = self.qty
        cxl_req_msg[41] = self.clord_id
        self.set_instrument(cxl_req_msg)
        cxl_req_msg[FTag.Side] = self.side
        cxl_req_msg[FTag.TransactTime] = self.current_datetime()

        return cxl_req_msg

    def replace_req(self, price: float, qty: float) -> FIXMessage:
        if not self.can_replace():
            raise FIXError("Order cannot be replaced")

        if isnan(price) or price == self.price:
            price = self.price
        if isnan(qty) or qty == self.qty or qty == 0:
            qty = self.qty

        if price == self.price and qty == self.qty:
            raise FIXError("no price / qty change in replace_req")

        assert not self.orig_clord_id
        self.orig_clord_id = self.clord_id
        self.clord_id = self.next_clord()

        m = FIXMessage(FMsg.ORDERCANCELREPLACEREQUEST)
        m[FTag.ClOrdID] = self.clord_id
        m[FTag.OrigClOrdID] = self.orig_clord_id
        m[FTag.OrdType] = self.ord_type
        self.set_instrument(m)
        self.set_price_qty(m, price, qty)
        m[FTag.Side] = self.side
        m[FTag.TransactTime] = self.current_datetime()

        return m
