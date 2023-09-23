import enum


class StrEnum(enum.Enum):
    def __str__(self):
        return str(self.value)

    def __eq__(self, o):
        return self.value == str(o)

    def __hash__(self):
        return hash(self.value)


class FOrdSide(StrEnum):
    BUY = "1"
    SELL = "2"
    BUY_MINUS = "3"
    SELL_PLUS = "4"
    SELL_SHORT = "5"
    SELL_SHORT_EXEMPT = "6"
    UNDISCLOSED = "7"
    CROSS = "8"
    CROSS_SHORT = "9"
    CROSS_SHORT_EXEMPT = "A"
    AS_DEFINED = "B"
    OPPOSITE = "C"
    SUBSCRIBE = "D"
    REDEEM = "E"
    LEND = "F"
    BORROW = "G"


class FOrdType(StrEnum):
    MARKET = "1"
    LIMIT = "2"
    STOP = "3"
    STOP_LIMIT = "4"
    WITH_OR_WITHOUT = "6"
    LIMIT_OR_BETTER = "7"
    LIMIT_WITH_OR_WITHOUT = "8"
    ON_BASIS = "9"
    PREVIOUSLY_QUOTED = "D"
    PREVIOUSLY_INDICATED = "E"
    FOREX_SWAP = "G"
    FUNARI = "I"
    MARKET_IF_TOUCHED = "J"
    MARKET_WITH_LEFT_OVER_AS_LIMIT = "K"
    PREVIOUS_FUND_VALUATION_POINT = "L"
    NEXT_FUND_VALUATION_POINT = "M"
    PEGGED = "P"


class FOrdStatus(StrEnum):
    CREATED = "Z"  # IMPORTANT: this one is for internal use, non FIX!
    NEW = "0"
    PARTIALLY_FILLED = "1"
    FILLED = "2"
    DONE_FOR_DAY = "3"
    CANCELED = "4"
    PENDING_CANCEL = "6"
    STOPPED = "7"
    REJECTED = "8"
    SUSPENDED = "9"
    PENDING_NEW = "A"
    CALCULATED = "B"
    EXPIRED = "C"
    ACCEPTED_FOR_BIDDING = "D"
    PENDING_REPLACE = "E"


class FExecType(StrEnum):
    NEW = "0"
    DONE_FOR_DAY = "3"
    CANCELED = "4"
    REPLACED = "5"
    PENDING_CANCEL = "6"
    STOPPED = "7"
    REJECTED = "8"
    SUSPENDED = "9"
    PENDING_NEW = "A"
    CALCULATED = "B"
    EXPIRED = "C"
    RESTATED = "D"
    PENDING_REPLACE = "E"
    TRADE = "F"
    TRADE_CORRECT = "G"
    TRADE_CANCEL = "H"
    ORDER_STATUS = "I"
