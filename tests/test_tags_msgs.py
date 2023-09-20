import pytest

from asyncfix import FMsg, FTag


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
    assert FMsg.HEARTBEAT == "0"
    assert FMsg.HEARTBEAT != 0
    assert str(FMsg.HEARTBEAT) == "0"
    assert f"{FMsg.HEARTBEAT}" == "0"
    assert FMsg("0") == FMsg.HEARTBEAT
    assert "0" in FMsg
    assert 0 not in FMsg
    assert hash(FMsg.HEARTBEAT) == hash("0")
    assert FMsg.HEARTBEAT in FMsg
