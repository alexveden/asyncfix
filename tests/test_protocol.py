import pytest

from asyncfix.protocol import FMsgType, FTag


def test_tags():
    assert FTag.Account == "1"
    assert FTag.Account == 1
    assert str(FTag.Account) == "1"
    assert f"{FTag.Account}" == "1"
    assert FTag("1") == "1"
    assert FTag("1") == FTag.Account
    assert FTag(FTag.Account) == FTag.Account
    assert FTag.Account in FTag
    assert "1" in FTag
    assert 1 in FTag
    assert 1102938109238 not in FTag
    assert "asdad" not in FTag
    assert hash(FTag.Account) == hash("1")


def test_msgtype():
    assert FMsgType.HEARTBEAT == "0"
    assert FMsgType.HEARTBEAT != 0
    assert str(FMsgType.HEARTBEAT) == "0"
    assert f"{FMsgType.HEARTBEAT}" == "0"
    assert FMsgType("0") == FMsgType.HEARTBEAT
    assert "0" in FMsgType
    assert 0 not in FMsgType
    assert hash(FMsgType.HEARTBEAT) == hash("0")
