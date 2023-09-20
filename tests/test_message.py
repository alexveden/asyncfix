import pickle
import unittest

import pytest

from asyncfix import FTag
from asyncfix.message import (
    DuplicatedTagError,
    FIXContext,
    FIXMessage,
    FIXMessageError,
    RepeatingTagError,
    TagNotFoundError,
)


def test_init_construction():
    msg = FIXMessage(
        "AB", {11: "clordis", "1": "account", FTag.Price: 21.21, FTag.OrderQty: 2}
    )
    assert msg[11] == "clordis"
    assert msg[FTag.Account] == "account"
    assert msg[FTag.Price] == "21.21"
    assert msg[FTag.OrderQty] == "2"


def test_tag_errors():
    msg = FIXMessage("AB")
    msg["45"] = "dgd"

    with pytest.raises(TagNotFoundError) as exc:
        msg["99"]
    with pytest.raises(TagNotFoundError) as exc:
        msg.get("99")

    assert msg.get("99", 100) == 100

    with pytest.raises(DuplicatedTagError, match="tag=45 already exists"):
        msg[45] = "aaa"

    with pytest.raises(FIXMessageError, match="Tags must be only integers"):
        msg["abs"] = "aaa"

    msg[45] = RepeatingTagError
    with pytest.raises(
        RepeatingTagError, match="tag=45 was repeated, possible undefined "
    ):
        msg[45]


def test_groups():
    msg = FIXMessage("AB")

    msg.set_group(2023, [{1: "a", 2: "b"}, FIXContext({1: "c", 2: "d"})])
    msg.add_group(2023, {1: "e", 4: "f"})

    with pytest.raises(FIXMessageError, match="Expected FIXContext in group, got "):
        msg.add_group(2023, None)

    g = msg.get_group_by_index(2023, 0)
    assert isinstance(g, FIXContext)
    assert g[1] == "a"
    assert g[2] == "b"

    g = msg.get_group_by_index(2023, 1)
    assert isinstance(g, FIXContext)
    assert g[1] == "c"
    assert g[2] == "d"

    g = msg.get_group_by_index(2023, 2)
    assert isinstance(g, FIXContext)
    assert g[1] == "e"
    assert g[4] == "f"

    with pytest.raises(
        TagNotFoundError, match="index is out of range of tag=2023 group"
    ):
        g = msg.get_group_by_index(2023, 3)

    assert msg.is_group(2023)


def test_msg_construction():
    msg = FIXMessage("AB")
    msg["45"] = "dgd"
    assert msg["45"] == "dgd"
    assert "45" in msg
    assert 45 in msg
    del msg["45"]
    assert "45" not in msg

    msg["45"] = "dgd"
    assert msg["45"] == "dgd"
    msg.set("32", "aaaa")
    msg.set("323", "bbbb")

    rptgrp1 = FIXContext()
    rptgrp1.set("611", "aaa")
    rptgrp1.set("612", "bbb")
    rptgrp1.set("613", "ccc")

    msg.add_group("444", rptgrp1, 0)

    rptgrp2 = FIXContext({611: "zzz", 612: "yyy", "613": "xxx"})
    msg.add_group("444", rptgrp2, 1)

    assert "45=dgd|32=aaaa|323=bbbb|444=2=>[611=aaa|612=bbb|613=ccc,"
    " 611=zzz|612=yyy|613=xxx]" == str(msg)

    msg.remove_group("444", 1)
    assert "45=dgd|32=aaaa|323=bbbb|444=1=>[611=aaa|612=bbb|613=ccc]" == str(msg)

    msg.add_group("444", rptgrp2, 1)

    rptgrp3 = FIXContext()
    rptgrp3.set("611", "ggg")
    rptgrp3.set("612", "hhh")
    rptgrp3.set("613", "jjj")
    rptgrp2.add_group("445", rptgrp3, 0)
    assert "45=dgd|32=aaaa|323=bbbb|444=2=>[611=aaa|612=bbb|613=ccc,"
    " 611=zzz|612=yyy|613=xxx|445=1=>[611=ggg|612=hhh|613=jjj]]" == str(msg)

    grp = msg.get_group_by_tag("444", "612", "yyy")
    assert "611=zzz|612=yyy|613=xxx|445=1=>[611=ggg|612=hhh|613=jjj]" == str(grp)


def testPickle():
    msg = FIXMessage("AB")
    msg.set("45", "dgd")
    msg.set("32", "aaaa")
    msg.set("323", "bbbb")

    rptgrp1 = FIXContext()
    rptgrp1.set("611", "aaa")
    rptgrp1.set("612", "bbb")
    rptgrp1.set("613", "ccc")

    msg.add_group("444", rptgrp1, 0)

    str = pickle.dumps(msg)

    msg2 = pickle.loads(str)
    assert msg == msg2
