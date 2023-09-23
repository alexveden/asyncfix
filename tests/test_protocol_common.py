import pytest

from asyncfix.protocol.common import FExecType, FOrdSide, FOrdStatus, FOrdType


def test_exec_type():
    assert FExecType.NEW == "0"
    assert FExecType.NEW in {"0"}
    assert "0" in {FExecType.NEW}


def test_ord_size():
    assert FOrdSide.BUY == "1"
    assert FOrdSide.SELL == "2"
    assert FOrdSide.BUY in {"1"}
    assert "1" in {FOrdSide.BUY}


def test_ord_status():
    assert FOrdStatus.CREATED == "Z"  # Non FIX! Only for internal use
    assert FOrdStatus.NEW == "0"
    assert FOrdStatus.NEW in {"0"}
    assert "0" in {FOrdStatus.NEW}
