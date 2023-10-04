import pickle
import unittest

import pytest

from asyncfix import FIXMessage, FTag
from asyncfix.errors import (
    DuplicatedTagError,
    FIXMessageError,
    RepeatingTagError,
    TagNotFoundError,
)
from asyncfix.message import FIXContainer


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

    assert 45 in msg
    del msg[45]
    assert 45 not in msg

    with pytest.raises(FIXMessageError, match="Tags must be only integers"):
        msg["abs"] = "aaa"

    msg[45] = RepeatingTagError
    with pytest.raises(
        RepeatingTagError, match="tag=45 was repeated, possible undefined "
    ):
        msg[45]


def test_groups():
    msg = FIXMessage("AB")

    msg.set_group(2023, [{1: "a", 2: "b"}, FIXContainer({1: "c", 2: "d"})])

    assert msg.get_group_by_tag(2023, 1, "a") == {1: "a", 2: "b"}

    with pytest.raises(
        TagNotFoundError, match="get_group_by_tag: tag=2023 gtag=1 gvalue='z' missing"
    ):
        assert msg.get_group_by_tag(2023, 1, "z") == "1=a|2=b"

    with pytest.raises(
        DuplicatedTagError, match="group with tag='2023' already exists"
    ):
        msg.set_group(2023, [{1: "a", 2: "b"}, FIXContainer({1: "c", 2: "d"})])

    with pytest.raises(
        FIXMessageError, match="groups must be a list of FIXContext or dict"
    ):
        msg.set_group(2022, [{1: "a", 2: "b"}, 2123])

    msg.add_group(2023, {1: "e", 4: "f"})

    with pytest.raises(FIXMessageError, match="Expected FIXContext in group, got "):
        msg.add_group(2023, None)

    g = msg.get_group_by_index(2023, 0)
    assert isinstance(g, FIXContainer)
    assert g[1] == "a"
    assert g[2] == "b"

    g = msg.get_group_by_index(2023, 1)
    assert isinstance(g, FIXContainer)
    assert g[1] == "c"
    assert g[2] == "d"

    g = msg.get_group_by_index(2023, 2)
    assert isinstance(g, FIXContainer)
    assert g[1] == "e"
    assert g[4] == "f"

    with pytest.raises(
        TagNotFoundError, match="index is out of range of tag=2023 group"
    ):
        g = msg.get_group_by_index(2023, 3)

    assert msg.is_group(2023)

    with pytest.raises(
        FIXMessageError, match="You are trying to get group as simple tag"
    ):
        # Getting group as simple tag is not allowed
        g = msg[2023]


def test_init_group_construction():
    msg = FIXMessage(
        "AB",
        {
            11: "clordis",
            "1": "account",
            2023: [{1: "a", 2: "b"}, FIXContainer({1: "c", 2: "d"})],
        },
    )

    g = msg.get_group_by_index(2023, 0)
    assert isinstance(g, FIXContainer)
    assert g[1] == "a"
    assert g[2] == "b"

    g = msg.get_group_by_index(2023, 1)
    assert isinstance(g, FIXContainer)
    assert g[1] == "c"
    assert g[2] == "d"


def test_msg_construction():
    msg = FIXMessage("AB")
    msg["45"] = "dgd"
    assert msg["45"] == "dgd"
    assert "45" in msg
    assert 45 in msg

    msg.set("32", "aaaa")
    msg.set("323", "bbbb")

    rptgrp1 = FIXContainer()
    rptgrp1.set("611", "aaa")
    rptgrp1.set("612", "bbb")
    rptgrp1.set("613", "ccc")

    msg.add_group("444", rptgrp1, 0)

    rptgrp2 = FIXContainer({611: "zzz", 612: "yyy", "613": "xxx"})
    msg.add_group("444", rptgrp2, 1)

    assert "45=dgd|32=aaaa|323=bbbb|444=2=>[611=aaa|612=bbb|613=ccc,"
    " 611=zzz|612=yyy|613=xxx]" == str(msg)

    msg.add_group("444", rptgrp2, 1)

    rptgrp3 = FIXContainer()
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

    rptgrp1 = FIXContainer()
    rptgrp1.set("611", "aaa")
    rptgrp1.set("612", "bbb")
    rptgrp1.set("613", "ccc")

    msg.add_group("444", rptgrp1, 0)

    str = pickle.dumps(msg)

    msg2 = pickle.loads(str)
    assert msg == msg2


def test_dict_contains():
    msg = FIXMessage(
        "AB", {11: "clordis", "1": "account", FTag.Price: 21.21, FTag.OrderQty: 2}
    )
    assert msg[11] == "clordis"
    assert msg[FTag.Account] == "account"
    assert msg[FTag.Price] == "21.21"
    assert msg[FTag.OrderQty] == "2"

    assert {11: "clordis"} in msg
    assert {12: "clordis"} not in msg
    assert {11: "clordis", "2": "account"} not in msg
    assert {11: "clordis1"} not in msg

    msg.add_group("444", {1: "ok"})
    with pytest.raises(
        FIXMessageError,
        match="__contains__ supports only simple tags, got group at tag=444",
    ):
        assert {444: "clordis"} in msg


def test_dict_equals():
    msg = FIXMessage(
        "AB", {11: "clordis", "1": "account", FTag.Price: 21.21, FTag.OrderQty: 2}
    )
    assert msg[11] == "clordis"
    assert msg[FTag.Account] == "account"
    assert msg[FTag.Price] == "21.21"
    assert msg[FTag.OrderQty] == "2"

    assert msg != "aaldsa"

    assert {11: "clordis", 1: "account", FTag.Price: 21.21, FTag.OrderQty: 2} in msg
    assert {11: "clordis", 1: "account", FTag.Price: 21.21, FTag.OrderQty: 2} == msg
    assert {12: "clordis", 1: "account", FTag.Price: 21.21, FTag.OrderQty: 2} != msg
    assert {11: "clordis1", 1: "account", FTag.Price: 21.21, FTag.OrderQty: 2} != msg

    # Ignoring tags
    msg[FTag.BeginString] = "FIX.4.4"
    assert {11: "clordis", 1: "account", FTag.Price: 21.21, FTag.OrderQty: 2} == msg
    msg[FTag.BodyLength] = "100"
    assert {11: "clordis", 1: "account", FTag.Price: 21.21, FTag.OrderQty: 2} == msg
    msg[FTag.CheckSum] = "100"
    assert {11: "clordis", 1: "account", FTag.Price: 21.21, FTag.OrderQty: 2} == msg
    msg[FTag.MsgType] = "1"
    assert {11: "clordis", "1": "account", FTag.Price: 21.21, FTag.OrderQty: 2} == msg

    # Other tag fails
    msg[2000] = "1"
    assert {11: "clordis", "1": "account", FTag.Price: 21.21, FTag.OrderQty: 2} != msg

    assert {
        11: "clordis",
        "1": "account",
        FTag.Price: 21.21,
        FTag.OrderQty: 2,
        2000: 1,
    } == msg

    msg.add_group(555, {1: "foo"})
    with pytest.raises(
        FIXMessageError,
        match="fix message __eq__ .* supports only simple tags, got group at tag=555",
    ):
        assert {
            11: "clordis",
            "1": "account",
            FTag.Price: 21.21,
            FTag.OrderQty: 2,
            2000: 1,
            555: [{1: "foo"}],
        } == msg


def test_query():
    msg = FIXMessage(
        "AB",
        {
            11: "clordis",
            "1": "account",
            FTag.Price: 21.21,
            FTag.OrderQty: 2,
            21238: "test",
        },
    )
    assert msg[11] == "clordis"
    assert msg[FTag.Account] == "account"
    assert msg[FTag.Price] == "21.21"
    assert msg[FTag.OrderQty] == "2"

    assert {
        "11": "clordis",
        "1": "account",
        FTag.Price: "21.21",
        FTag.OrderQty: "2",
        "21238": "test",
    } == msg.query()
    assert {FTag.ClOrdID: "clordis", FTag.Account: "account"} != msg.query(12, 1)
