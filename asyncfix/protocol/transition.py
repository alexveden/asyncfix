from typing import Optional

from asyncfix import FMsg
from asyncfix.errors import FIXError
from asyncfix.protocol.common import FOrdStatus, FExecType


def get_status_transitions(
    fix_msg_type: FMsg,
    order_status: FOrdStatus,
    msg_exec_type: FExecType,
) -> dict[Optional[FOrdStatus], bool | type[FIXError] | None]:
    match fix_msg_type:
        case FMsg.EXECUTIONREPORT:
            if order_status == FOrdStatus.PENDING_REPLACE:
                return get_status_transitions_execution_report_pending_cancel(
                    msg_exec_type
                )
            return get_status_transitions_execution_report(order_status)
        case FMsg.ORDERCANCELREJECT:
            return get_status_transitions_order_cancel_reject(order_status)
        case FMsg.ORDERCANCELREQUEST | FMsg.ORDERCANCELREPLACEREQUEST:
            return get_status_transitions_order_cancel_request(order_status)
        case _:
            raise FIXError(f"No status transition table for {fix_msg_type=}")


def get_status_transitions_execution_report_pending_cancel(
    msg_exec_type: FExecType,
) -> dict[Optional[FOrdStatus], bool | type[FIXError] | None]:
    statuses: dict[
        Optional[FExecType], dict[Optional[FOrdStatus], bool | type[FIXError] | None]
    ] = {
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
    }
    return statuses.get(msg_exec_type, statuses[None])


def get_status_transitions_execution_report(
    order_status: FOrdStatus,
) -> dict[Optional[FOrdStatus], bool | type[FIXError] | None]:
    statuses: dict[
        Optional[FOrdStatus], dict[Optional[FOrdStatus], bool | type[FIXError] | None]
    ] = {
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
    }
    return statuses.get(order_status, statuses[None])


def get_status_transitions_order_cancel_reject(
    order_status: FOrdStatus,
) -> dict[Optional[FOrdStatus], bool | type[FIXError] | None]:
    statuses: dict[
        Optional[FOrdStatus], dict[Optional[FOrdStatus], bool | type[FIXError] | None]
    ] = {
        None: {
            FOrdStatus.CREATED: FIXError,
            FOrdStatus.ACCEPTED_FOR_BIDDING: FIXError,
            None: True,
        }
    }
    return statuses.get(order_status, statuses[None])


def get_status_transitions_order_cancel_request(
    order_status: FOrdStatus,
) -> dict[Optional[FOrdStatus], bool | type[FIXError] | None]:
    statuses: dict[
        Optional[FOrdStatus], dict[Optional[FOrdStatus], bool | type[FIXError] | None]
    ] = {
        FOrdStatus.PENDING_CANCEL: {None: None},
        FOrdStatus.PENDING_REPLACE: {None: None},
        FOrdStatus.NEW: {None: True},
        FOrdStatus.SUSPENDED: {None: True},
        FOrdStatus.PARTIALLY_FILLED: {None: True},
        None: {None: FIXError},
    }
    return statuses.get(order_status, statuses[None])
