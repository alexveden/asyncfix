import pytest

from asyncfix import FIXMessage, FMsg, FTag
from asyncfix.session import FIXSession


def test_init():
    s = FIXSession("1", "target", "sender")
    assert s.key == "1"
    assert s.target_comp_id == "target"
    assert s.sender_comp_id == "sender"

    assert s.next_num_in is None
    assert s.next_num_out is None


def test_hash():
    s = FIXSession("1", "target", "sender")
    assert hash(s) == hash((s.target_comp_id, s.sender_comp_id))


def test_equality():
    s1 = FIXSession("1", "target", "sender")
    s2 = FIXSession("2", "target", "sender")
    s3 = FIXSession("1", "target1", "sender")
    s4 = FIXSession("1", "target", "sender2")

    assert s1 == s2
    assert s1 != s3
    assert s1 != s4
    assert s1 == ("target", "sender")
    assert s1 != ("target",)
    assert s1 != ("target", "sender", "unexp")
    assert s1 != ("1target", "sender")
    assert s1 != ("target", "1sender")
    assert s1 != "target,sender"


def test_repr():
    s1 = FIXSession("1", "target", "sender")
    s1.next_num_out = 1
    s1.next_num_in = 1
    assert "FIXSession(key=1, target=target sender=sender InSN=1 OutSN=1)" == repr(s1)


def test_validate_compid():
    s1 = FIXSession("1", "target", "sender")

    assert s1.validate_comp_ids("target", "sender")
    assert not s1.validate_comp_ids("sender", "target")


def test_allocate_next_num_out():
    s1 = FIXSession("1", "target", "sender")
    s1.next_num_out = 1
    assert s1.allocate_next_num_out() == "1"
    assert s1.next_num_out == 2


def test_set_next_num_in():
    s1 = FIXSession("1", "target", "sender")

    s1.next_num_in = 10

    assert s1.set_next_num_in(FIXMessage(FMsg.SEQUENCERESET)) == 0
    assert s1.next_num_in == 10

    assert s1.set_next_num_in(FIXMessage(FMsg.SEQUENCERESET, {FTag.NewSeqNo: 4})) == 3
    assert s1.next_num_in == 4

    assert s1.set_next_num_in(FIXMessage(FMsg.LOGON)) == 0
    assert s1.next_num_in == 4

    assert s1.set_next_num_in(FIXMessage(FMsg.LOGON, {FTag.MsgSeqNum: 3})) == -1
    assert s1.next_num_in == 4

    assert s1.set_next_num_in(FIXMessage(FMsg.LOGON, {FTag.MsgSeqNum: 5})) == -1
    assert s1.next_num_in == 4

    assert s1.set_next_num_in(FIXMessage(FMsg.LOGON, {FTag.MsgSeqNum: 4})) == 4
    assert s1.next_num_in == 5
