import os
import xml.etree.ElementTree as ET
from unittest.mock import patch

import pytest

from asyncfix import FIXMessage, FMsg, FTag
from asyncfix.codec import Codec
from asyncfix.errors import FIXMessageError
from asyncfix.protocol.protocol_fix44 import FIXProtocol44
from asyncfix.protocol.schema import (
    FIXSchema,
    SchemaComponent,
    SchemaField,
    SchemaGroup,
    SchemaMessage,
    SchemaSet,
)
from asyncfix.session import FIXSession

TEST_DIR = os.path.abspath(os.path.dirname(__file__))


@pytest.fixture
def fix_simple_xml():
    return ET.parse(os.path.join(TEST_DIR, "schema_fix_simple.xml"))


@pytest.fixture
def fix_circular_invalid_xml():
    return ET.parse(os.path.join(TEST_DIR, "schema_fix_comp_circular.xml"))


def test_schema_field():
    f = SchemaField("1", "Account", "STRING")
    f2 = SchemaField("11", "ClOrdID", "STRING")
    assert f.tag == "1"
    assert f.name == "Account"
    assert f.ftype == "STRING"
    assert f.values == {}
    # no values in SchemaField any allowed
    assert f.validate_value("adslkajdlskj")

    f.values["test"] = "1"
    assert f.values == {"test": "1"}
    with pytest.raises(
        FIXMessageError, match="Field=Account value expected to be one of the "
    ):
        assert not f.validate_value("adslkajdlskj")
    assert f.validate_value("test")

    assert f != f2
    assert f == f
    assert f == "Account"
    assert f == "1"
    assert f == 1
    assert f != float("123")

    fields = {f: 1, f2: 2}

    assert f in fields
    assert fields[f] == 1
    assert fields[f2] == 2
    assert fields["Account"] == 1

    # search by tag not supported
    assert "1" not in fields
    assert 1 not in fields


def test_schema_set():
    f = SchemaField("1", "Account", "STRING")
    f2 = SchemaField("11", "ClOrdID", "STRING")

    s = SchemaSet("myset")
    s.add(f, True)
    s.add(f2, False)
    assert hash(s) == hash("myset")

    with pytest.raises(ValueError, match="Unsupported field_or_set type, got"):
        s.add("notsupported", False)

    with pytest.raises(ValueError, match="tag property is not supported"):
        s.tag

    assert f in s
    assert f2 in s
    assert "Account" in s

    assert s.name == "myset"
    assert len(s.members) == 2
    assert s.required[f]
    assert not s.required[f2]

    # Error type for group
    fg = SchemaField("73", "NoOrders", "STRING")
    with pytest.raises(
        ValueError, match="SchemaSet expected to have group field with "
    ):
        SchemaSet("NoOrders", field=fg)

    with pytest.raises(FIXMessageError, match="item looks like tag"):
        assert "1" in s

    with pytest.raises(FIXMessageError, match="item looks like tag"):
        assert 1 in s

    with pytest.raises(FIXMessageError, match="item looks like tag"):
        s["1"]

    with pytest.raises(FIXMessageError, match="item looks like tag"):
        s[1]


def test_schema_set_included_components():
    f = SchemaField("1", "Account", "STRING")
    f2 = SchemaField("11", "ClOrdID", "STRING")

    s = SchemaSet("myset")
    s.add(f, True)

    s2 = SchemaSet("myset2")
    s2.add(f2, False)

    s.merge(s2)

    assert f in s
    assert f2 in s
    assert s == "myset"

    assert s.name == "myset"
    assert len(s.members) == 2
    assert s.required[f]
    assert not s.required[f2]


def test_schema_set__add_group():
    f = SchemaField("1", "Account", "STRING")
    f2 = SchemaField("11", "ClOrdID", "STRING")

    s = SchemaSet("myset")
    s.add(f, True)

    fg = SchemaField("73", "NoOrders", "NUMINGROUP")
    g = SchemaGroup(fg, False)
    assert g.tag == fg.tag
    assert not g.field_required
    assert g.field is fg
    assert g == fg
    assert g == "NoOrders"
    assert g == "73"
    assert g == 73

    s2 = SchemaSet("myset2")
    s2.add(g, False)

    s.merge(s2)

    assert s.name == "myset"
    assert len(s.members) == 2
    assert s.members[f]
    assert isinstance(s.members[f], SchemaField)
    assert not s.required[g]

    assert f in s
    assert g in s
    assert "Account" in s
    assert "NoOrders" in s, s.members
    assert fg in s


def test_xml_init(fix_simple_xml):
    schema = FIXSchema(fix_simple_xml)

    f = schema.field2tag["AdvSide"]
    f2 = schema.tag2field["4"]

    assert f == f2
    assert f.validate_value("B")
    with pytest.raises(
        FIXMessageError, match="Field=AdvSide value expected to be one of the "
    ):
        assert not f.validate_value("Z")

    assert len(schema.components) == 3
    assert "ContraGrp" in schema.components
    assert "ContraGrp2" in schema.components
    assert "CommissionData" in schema.components
    c = schema.components["ContraGrp"]
    assert isinstance(c, SchemaComponent)
    assert c.name == "ContraGrp"
    assert c.field is None

    # Check messages
    assert schema.messages
    m = schema.messages["ExecutionReport"]
    assert isinstance(m, SchemaMessage)
    assert m.msg_type == "8"
    assert m.msg_cat == "app"
    assert isinstance(m["NoPartyIDs"], SchemaGroup)

    # Ensure group ordered!
    g = m["NoPartyIDs"]
    assert isinstance(g, SchemaGroup)
    assert ["PartyID", "PartyRole"] == list(g.members)

    # Check header
    assert len(schema.header.keys()) == 7
    assert schema.header.keys() == [
        "BeginString",
        "BodyLength",
        "MsgType",
        "SenderCompID",
        "TargetCompID",
        "MsgSeqNum",
        "SendingTime",
    ]
    field = schema.tag2field["8"]
    assert field in schema.header


def test_xml_circular_init(fix_circular_invalid_xml):
    with pytest.raises(
        RuntimeError,
        match=(
            r"Failed to resolve component circular reference.Failed components:"
            r" \['ContraGrp'\]"
        ),
    ):
        schema = FIXSchema(fix_circular_invalid_xml)


def test_xml_real_schema():
    tree = ET.parse(os.path.join(TEST_DIR, "FIX44.xml"))
    schema = FIXSchema(tree)

    assert len(schema.messages) == 93
    assert len(schema.components) == 104
    assert len(schema.field2tag) == 912
    assert schema.types == {
        "AMT",
        "BOOLEAN",
        "CHAR",
        "COUNTRY",
        "CURRENCY",
        "DATA",
        "EXCHANGE",
        "FLOAT",
        "INT",
        "LENGTH",
        "LOCALMKTDATE",
        "MONTHYEAR",
        "MULTIPLEVALUESTRING",
        "NUMINGROUP",
        "PERCENTAGE",
        "PRICE",
        "PRICEOFFSET",
        "QTY",
        "SEQNUM",
        "STRING",
        "UTCDATEONLY",
        "UTCTIMEONLY",
        "UTCTIMESTAMP",
    }

    assert "ExecutionReport" in schema.messages


def test_xml_real_schema_tt():
    tree = ET.parse(os.path.join(TEST_DIR, "TT-FIX44.xml"))
    schema = FIXSchema(tree)

    assert len(schema.messages) == 40
    assert len(schema.components) == 0
    assert len(schema.field2tag) == 611
    assert schema.types == {
        "AMT",
        "BOOLEAN",
        "CHAR",
        "CURRENCY",
        "DATA",
        "DAYOFMONTH",
        "EXCHANGE",
        "FLOAT",
        "INT",
        "LENGTH",
        "LOCALMKTDATE",
        "MONTHYEAR",
        "MULTIPLESTRINGVALUE",
        "NUMINGROUP",
        "PRICE",
        "QTY",
        "SEQNUM",
        "STRING",
        "UTCDATEONLY",
        "UTCTIMEONLY",
        "UTCTIMESTAMP",
    }

    assert "ExecutionReport" in schema.messages

    # Each message can have different group members of the same group
    m = schema.messages["MarketDataSnapshot"]
    g = m["NoMDEntries"]
    assert isinstance(g, SchemaGroup)
    assert g.keys() == [
        "MDEntryType",
        "MDEntryPx",
        "MDEntrySize",
        "MDEntryDate",
        "MDEntryTime",
        "MDEntryPositionNo",
        "NumberOfOrders",
    ]

    # Each message can have different group members of the same group
    m = schema.messages["MarketDataIncrementalRefresh"]
    g = m["NoMDEntries"]
    assert isinstance(g, SchemaGroup)
    assert g.keys() == [
        "MDUpdateAction",
        "MDEntryType",
        "Symbol",
        "SecurityDesc",
        "Product",
        "SecurityType",
        "SecuritySubType",
        "MaturityMonthYear",
        "MaturityDate",
        "MaturityDay",
        "PutOrCall",
        "StrikePrice",
        "OptAttribute",
        "DeliveryTerm",
        "DeliveryDate",
        "SecurityID",
        "SecurityExchange",
        "ExDestination",
        "CFICode",
        "Currency",
        "MDEntryPx",
        "MDEntrySize",
        "MDEntryDate",
        "MDEntryTime",
        "MDEntryPositionNo",
        "SecondaryOrderID",
        "NumberOfOrders",
    ]


def test_schema_validation(fix_simple_xml):
    schema = FIXSchema(fix_simple_xml)

    m = FIXMessage(FMsg.EXECUTIONREPORT, {FTag.OrderID: "1234"})
    schema.validate(m)

    m = FIXMessage("1ASD")
    with pytest.raises(FIXMessageError, match="msg_type=`1ASD` not in schema"):
        schema.validate(m)

    m = FIXMessage(FMsg.EXECUTIONREPORT, {})
    with pytest.raises(
        FIXMessageError,
        match="Missing required field=SchemaField.*OrderID|37",
    ):
        schema.validate(m)

    m = FIXMessage(FMsg.EXECUTIONREPORT, {FTag.OrderID: "1234", "12309812": "12"})
    with pytest.raises(
        FIXMessageError,
        match="msg tag=12309812 not in schema",
    ):
        schema.validate(m)

    m = FIXMessage(FMsg.EXECUTIONREPORT, {FTag.OrderID: "1234", FTag.AdvSide: "1"})
    with pytest.raises(
        FIXMessageError,
        match="msg field=AdvSide.*not allowed in SchemaMessage.*name=ExecutionReport",
    ):
        schema.validate(m)

    m = FIXMessage(
        FMsg.EXECUTIONREPORT, {FTag.OrderID: "1234", FTag.NoContraBrokers: "1"}
    )
    with pytest.raises(
        FIXMessageError,
        match="msg tag=382 val=1 must be a group",
    ):
        schema.validate(m)

    m = FIXMessage(FMsg.EXECUTIONREPORT)
    m.set_group(FTag.OrderID, [{1: "1`231"}])
    with pytest.raises(
        FIXMessageError,
        match="msg tag=37 val=.* must be a tag, got group",
    ):
        schema.validate(m)

    m = FIXMessage(FMsg.EXECUTIONREPORT, {FTag.OrderID: "1234"})
    m.set_group(FTag.NoPartyIDs, [{1: "test"}])
    with (
        patch("asyncfix.protocol.schema.SchemaGroup.validate_group") as mock_valgrp,
        patch("asyncfix.protocol.schema.SchemaField.validate_value") as mock_valfield,
    ):
        schema.validate(m)

    assert mock_valgrp.called
    assert mock_valgrp.call_count == 1
    assert len(mock_valgrp.call_args[0][0]) == 1
    assert mock_valgrp.call_args[1] == {}
    assert mock_valgrp.call_args[0][0][0] == {1: "test"}


def test_field_type_validation__int():
    f = SchemaField("1", "test", "INT")

    assert f.validate_value("1")
    assert f.validate_value("0")
    assert f.validate_value("-1")

    with pytest.raises(
        FIXMessageError, match="validation error .*: invalid literal for int"
    ):
        assert f.validate_value("as")

    with pytest.raises(
        FIXMessageError, match="validation error .*: invalid literal for int"
    ):
        assert f.validate_value("10.2")

    with pytest.raises(
        FIXMessageError, match="validation error .*: invalid literal for int"
    ):
        assert f.validate_value("10.0")


def test_field_type_validation__seqnum():
    f = SchemaField("1", "test", "SEQNUM")

    assert f.validate_value("1")

    with pytest.raises(
        FIXMessageError, match="validation error .*: invalid literal for int"
    ):
        assert f.validate_value("as")

    with pytest.raises(
        FIXMessageError, match="validation error .*: invalid literal for int"
    ):
        assert f.validate_value("10.2")

    with pytest.raises(
        FIXMessageError, match="validation error .*: invalid literal for int"
    ):
        assert f.validate_value("10.0")

    with pytest.raises(FIXMessageError, match="validation error .*: zero value"):
        assert f.validate_value("0")

    with pytest.raises(FIXMessageError, match="validation error .*: negative value"):
        assert f.validate_value("-1")


def test_field_type_validation__numingroup():
    f = SchemaField("1", "test", "NUMINGROUP")

    assert f.validate_value("1")

    with pytest.raises(
        FIXMessageError, match="validation error .*: invalid literal for int"
    ):
        assert f.validate_value("as")

    with pytest.raises(
        FIXMessageError, match="validation error .*: invalid literal for int"
    ):
        assert f.validate_value("10.2")

    with pytest.raises(
        FIXMessageError, match="validation error .*: invalid literal for int"
    ):
        assert f.validate_value("10.0")

    with pytest.raises(FIXMessageError, match="validation error .*: zero value"):
        assert f.validate_value("0")

    with pytest.raises(FIXMessageError, match="validation error .*: negative value"):
        assert f.validate_value("-1")


def test_field_type_validation__dayofmonth():
    f = SchemaField("1", "test", "DAYOFMONTH")

    for i in range(1, 32):
        assert f.validate_value(str(i))

    with pytest.raises(
        FIXMessageError, match="validation error .*: invalid literal for int"
    ):
        assert f.validate_value("as")

    with pytest.raises(
        FIXMessageError, match="validation error .*: invalid literal for int"
    ):
        assert f.validate_value("10.2")

    with pytest.raises(
        FIXMessageError, match="validation error .*: invalid literal for int"
    ):
        assert f.validate_value("10.0")

    with pytest.raises(FIXMessageError, match="validation error .*: out of range "):
        assert f.validate_value("0")

    with pytest.raises(FIXMessageError, match="validation error .*: out of range"):
        assert f.validate_value("32")


def test_field_type_validation__float():
    f = SchemaField("1", "test", "FLOAT")

    assert f.validate_value("1")
    assert f.validate_value("0.0")
    assert f.validate_value("1.1231")
    assert f.validate_value("-1.12310923810281")

    with pytest.raises(
        FIXMessageError, match="validation error .*: could not convert string to float"
    ):
        assert f.validate_value("as")

    with pytest.raises(
        FIXMessageError, match="validation error .*: not isfinite number"
    ):
        assert f.validate_value("nan")

    with pytest.raises(
        FIXMessageError, match="validation error .*: not isfinite number"
    ):
        assert f.validate_value("inf")


def test_field_type_validation__qty():
    f = SchemaField("1", "test", "QTY")

    assert f.validate_value("1")
    assert f.validate_value("0.0")
    assert f.validate_value("1.1231")
    assert f.validate_value("-1.12310923810281")

    with pytest.raises(
        FIXMessageError, match="validation error .*: could not convert string to float"
    ):
        assert f.validate_value("as")

    with pytest.raises(
        FIXMessageError, match="validation error .*: not isfinite number"
    ):
        assert f.validate_value("nan")

    with pytest.raises(
        FIXMessageError, match="validation error .*: not isfinite number"
    ):
        assert f.validate_value("inf")


def test_field_type_validation__price():
    f = SchemaField("1", "test", "PRICE")

    assert f.validate_value("1")
    assert f.validate_value("0.0")
    assert f.validate_value("1.1231")
    assert f.validate_value("-1.12310923810281")

    with pytest.raises(
        FIXMessageError, match="validation error .*: could not convert string to float"
    ):
        assert f.validate_value("as")

    with pytest.raises(
        FIXMessageError, match="validation error .*: not isfinite number"
    ):
        assert f.validate_value("nan")

    with pytest.raises(
        FIXMessageError, match="validation error .*: not isfinite number"
    ):
        assert f.validate_value("inf")


def test_field_type_validation__priceoffset():
    f = SchemaField("1", "test", "PRICEOFFSET")

    assert f.validate_value("1")
    assert f.validate_value("0.0")
    assert f.validate_value("1.1231")
    assert f.validate_value("-1.12310923810281")

    with pytest.raises(
        FIXMessageError, match="validation error .*: could not convert string to float"
    ):
        assert f.validate_value("as")

    with pytest.raises(
        FIXMessageError, match="validation error .*: not isfinite number"
    ):
        assert f.validate_value("nan")

    with pytest.raises(
        FIXMessageError, match="validation error .*: not isfinite number"
    ):
        assert f.validate_value("inf")


def test_field_type_validation__amt():
    f = SchemaField("1", "test", "AMT")

    assert f.validate_value("1")
    assert f.validate_value("0.0")
    assert f.validate_value("1.1231")
    assert f.validate_value("-1.12310923810281")

    with pytest.raises(
        FIXMessageError, match="validation error .*: could not convert string to float"
    ):
        assert f.validate_value("as")

    with pytest.raises(
        FIXMessageError, match="validation error .*: not isfinite number"
    ):
        assert f.validate_value("nan")

    with pytest.raises(
        FIXMessageError, match="validation error .*: not isfinite number"
    ):
        assert f.validate_value("inf")


def test_field_type_validation__percentage():
    f = SchemaField("1", "test", "PERCENTAGE")

    assert f.validate_value("1")
    assert f.validate_value("0.0")
    assert f.validate_value("1.1231")
    assert f.validate_value("-1.12310923810281")

    with pytest.raises(
        FIXMessageError, match="validation error .*: could not convert string to float"
    ):
        assert f.validate_value("as")

    with pytest.raises(
        FIXMessageError, match="validation error .*: not isfinite number"
    ):
        assert f.validate_value("nan")

    with pytest.raises(
        FIXMessageError, match="validation error .*: not isfinite number"
    ):
        assert f.validate_value("inf")


def test_field_type_validation__string():
    f = SchemaField("1", "test", "STRING")

    assert f.validate_value("1")
    assert f.validate_value("A")
    assert f.validate_value("-1.12310923810281")
    assert f.validate_value("Hey this is alphanum string ! Also, some @tags, #test")

    with pytest.raises(
        FIXMessageError, match="validation error .*: Value contains SOH char"
    ):
        assert f.validate_value("a\x01s")

    with pytest.raises(
        FIXMessageError, match="validation error .*: Value contains `=` char"
    ):
        assert f.validate_value("as some tag=values")


def test_field_type_validation__char():
    f = SchemaField("1", "test", "CHAR")

    assert f.validate_value("1")
    assert f.validate_value("A")
    assert f.validate_value("z")
    assert f.validate_value("!")

    with pytest.raises(FIXMessageError, match="max legth exceeded"):
        assert f.validate_value("as")


def test_field_type_validation__boolean():
    f = SchemaField("1", "test", "BOOLEAN")

    assert f.validate_value("Y")
    assert f.validate_value("N")

    with pytest.raises(FIXMessageError, match="out of subset"):
        assert f.validate_value("Z")

    with pytest.raises(FIXMessageError, match="max legth exceeded"):
        assert f.validate_value("ZA")


def test_field_type_validation__multiplestringvalue():
    f = SchemaField("1", "test", "MULTIPLESTRINGVALUE")

    assert f.validate_value("Y AS NA za")
    assert f.validate_value("N N 2 1 n")


def test_field_type_validation__country():
    f = SchemaField("1", "test", "COUNTRY")

    assert f.validate_value("RU")
    assert f.validate_value("US")

    with pytest.raises(FIXMessageError, match="max legth exceeded"):
        assert f.validate_value("ZAR")


def test_field_type_validation__currency():
    f = SchemaField("1", "test", "CURRENCY")

    assert f.validate_value("RUB")
    assert f.validate_value("USD")

    with pytest.raises(FIXMessageError, match="max legth exceeded"):
        assert f.validate_value("EURU")

    with pytest.raises(
        FIXMessageError, match="value contains non alphanumeric letters"
    ):
        assert f.validate_value("EU@")


def test_field_type_validation__exchange():
    f = SchemaField("1", "test", "EXCHANGE")

    assert f.validate_value("NYSE")
    assert f.validate_value("NQ")

    with pytest.raises(FIXMessageError, match="max legth exceeded"):
        assert f.validate_value("EUREx")


def test_field_type_validation__localmktdate():
    f = SchemaField("1", "test", "LOCALMKTDATE")

    assert f.validate_value("20230921")

    with pytest.raises(
        FIXMessageError, match="time data 'EUREx' does not match format '%Y%m%d'"
    ):
        assert f.validate_value("EUREx")

    with pytest.raises(FIXMessageError, match="unconverted data remains"):
        assert f.validate_value("20230921 14:00:00.12312")

    with pytest.raises(FIXMessageError, match="day is out of range for month"):
        assert f.validate_value("20230231")


def test_field_type_validation__utsdateonly():
    f = SchemaField("1", "test", "UTCDATEONLY")

    assert f.validate_value("20230921")

    with pytest.raises(
        FIXMessageError, match="time data 'EUREx' does not match format '%Y%m%d'"
    ):
        assert f.validate_value("EUREx")

    with pytest.raises(FIXMessageError, match="unconverted data remains"):
        assert f.validate_value("20230921 14:00:00.12312")

    with pytest.raises(FIXMessageError, match="day is out of range for month"):
        assert f.validate_value("20230231")


def test_field_type_validation__utctimestamp():
    f = SchemaField("1", "test", "UTCTIMESTAMP")

    assert f.validate_value("20230921-14:00:00")
    assert f.validate_value("20230921-14:00:00.123")
    assert f.validate_value("20230921-14:00:00.123456")

    with pytest.raises(FIXMessageError, match=" does not match format "):
        assert f.validate_value("EUREx")

    with pytest.raises(FIXMessageError, match="unconverted data remains"):
        assert f.validate_value("20230921-14:00:00.123456789")


def test_field_type_validation__utctimeonly():
    f = SchemaField("1", "test", "UTCTIMEONLY")

    assert f.validate_value("14:00:00")
    assert f.validate_value("14:00:00.123")
    assert f.validate_value("14:00:00.123456")

    with pytest.raises(FIXMessageError, match=" does not match format "):
        assert f.validate_value("EUREx")

    with pytest.raises(FIXMessageError, match="unconverted data remains"):
        assert f.validate_value("14:00:00.123456789")

    with pytest.raises(FIXMessageError, match=" does not match format "):
        assert f.validate_value("20230921 14:00:00.123456789")


def test_field_type_validation__monthyear():
    f = SchemaField("1", "test", "MONTHYEAR")

    assert f.validate_value("202309")
    assert f.validate_value("20230921")
    assert f.validate_value("202309w1")
    assert f.validate_value("202309w2")
    assert f.validate_value("202309w3")
    assert f.validate_value("202309w4")
    assert f.validate_value("202309w5")

    with pytest.raises(FIXMessageError, match=" does not match format "):
        assert f.validate_value("EUREx")

    with pytest.raises(FIXMessageError, match="remainder YYYYMM invalid"):
        assert f.validate_value("20230925w5")

    with pytest.raises(FIXMessageError, match="ww must be in w1,w2,w3,w4,w5"):
        assert f.validate_value("202309w6")


def test_field_type_validation__data():
    f = SchemaField("1", "test", "DATA")

    # pass all
    assert f.validate_value("202309\x01")


def test_field_type_validation__length():
    f = SchemaField("1", "test", "LENGTH")

    # pass all
    assert f.validate_value("202309")
    assert f.validate_value("-202309")


def test_field_type_validation__unsupported():
    f = SchemaField("1", "test", "UNSUPPORTED")

    # pass all
    with patch("asyncfix.protocol.schema.warnings.warn") as mock_warn:
        assert f.validate_value("202309")
        assert mock_warn.called
        assert "UNSUPPORTED" in mock_warn.call_args[0][0]


def test_schema_validation_group(fix_simple_xml):
    schema = FIXSchema(fix_simple_xml)
    assert schema[FTag.NoPartyIDs].tag == "453"
    assert schema[453].tag == "453"
    assert schema["453"].tag == "453"
    assert schema["NoPartyIDs"].tag == "453"

    m = schema.messages_types[FMsg.EXECUTIONREPORT]

    assert m.msg_type == FMsg.EXECUTIONREPORT
    g = m["NoPartyIDs"]
    assert isinstance(g, SchemaGroup)

    with pytest.raises(
        FIXMessageError, match="contains unsupported tag for SchemaGroup"
    ):
        msg_g = FIXMessage(
            FMsg.EXECUTIONREPORT,
            {
                FTag.NoPartyIDs: [
                    {FTag.PartyID: "asd", FTag.Account: "1"},
                    {FTag.PartyID: "asd", FTag.PartyRole: "asda"},
                ]
            },
        )
        g.validate_group(msg_g.get_group_list(FTag.NoPartyIDs))

    with pytest.raises(FIXMessageError, match="does not contain mandatory first tag"):
        msg_g = FIXMessage(
            FMsg.EXECUTIONREPORT,
            {
                FTag.NoPartyIDs: [
                    {FTag.PartyRole: "1"},
                    {FTag.PartyID: "asd", FTag.PartyRole: "asda"},
                ]
            },
        )
        g.validate_group(msg_g.get_group_list(FTag.NoPartyIDs))

    g = m["NoContraBrokers"]
    with pytest.raises(
        FIXMessageError, match="missing required field SchemaField.*ContraTrader|"
    ):
        msg_g = FIXMessage(
            FMsg.EXECUTIONREPORT,
            {
                FTag.NoContraBrokers: [
                    {FTag.ContraBroker: "1"},
                ]
            },
        )
        g.validate_group(msg_g.get_group_list(FTag.NoContraBrokers))

    g = m["NoContraBrokers"]
    with pytest.raises(FIXMessageError, match="incorrect tag order"):
        msg_g = FIXMessage(
            FMsg.EXECUTIONREPORT,
            {
                FTag.NoContraBrokers: [
                    {
                        FTag.ContraBroker: "1",
                        FTag.Commission: "10",
                        FTag.ContraTrader: "1",
                    },
                ]
            },
        )
        g.validate_group(msg_g.get_group_list(FTag.NoContraBrokers))

    g = m["NoContraBrokers"]
    with pytest.raises(
        FIXMessageError,
        match="Commission|12 validation error .* could not convert string to float:",
    ):
        msg_g = FIXMessage(
            FMsg.EXECUTIONREPORT,
            {
                FTag.NoContraBrokers: [
                    {
                        FTag.ContraBroker: "1",
                        FTag.ContraTrader: "1",
                        FTag.Commission: "asd",
                    },
                ]
            },
        )
        g.validate_group(msg_g.get_group_list(FTag.NoContraBrokers))


def test_schema_validation_group_nested(fix_simple_xml):
    schema = FIXSchema(fix_simple_xml)
    m = schema.messages_types[FMsg.EXECUTIONREPORT]

    g = m["NoContraBrokers"]

    with pytest.raises(
        FIXMessageError,
        match="tag=382 must be a group ",
    ):
        msg_g = FIXMessage(
            FMsg.EXECUTIONREPORT,
            {
                FTag.NoContraBrokers: [
                    {
                        FTag.ContraBroker: "1",
                        FTag.ContraTrader: "1",
                        FTag.Commission: "10",
                    },
                    {
                        FTag.ContraBroker: "1",
                        FTag.ContraTrader: "1",
                        FTag.Commission: "10",
                        FTag.NoContraBrokers: "2",
                    },
                ]
            },
        )
        g.validate_group(msg_g.get_group_list(FTag.NoContraBrokers))

    with pytest.raises(
        FIXMessageError,
        match=r"fixmessage=\[337=1\] does not contain mandatory first tag ",
    ):
        msg_g = FIXMessage(
            FMsg.EXECUTIONREPORT,
            {
                FTag.NoContraBrokers: [
                    {
                        FTag.ContraBroker: "1",
                        FTag.ContraTrader: "1",
                        FTag.Commission: "10",
                    },
                    {
                        FTag.ContraBroker: "1",
                        FTag.ContraTrader: "1",
                        FTag.Commission: "10",
                        FTag.NoContraBrokers: [{FTag.ContraTrader: "1"}],
                    },
                ]
            },
        )
        g.validate_group(msg_g.get_group_list(FTag.NoContraBrokers))


def test_schema_validation_header(fix_simple_xml):
    schema = FIXSchema(fix_simple_xml)

    m = FIXMessage(FMsg.EXECUTIONREPORT, {FTag.OrderID: "1234"})

    codec = Codec(FIXProtocol44())
    session = FIXSession("1", "TARG", "SEND")
    session.next_num_in = 1
    session.next_num_out = 1
    enc_m = codec.encode(m, session)

    dec_m, _, _ = codec.decode(enc_m.encode(), silent=False)

    schema.validate(dec_m)

    del dec_m[FTag.MsgSeqNum]
    with pytest.raises(
        FIXMessageError, match=r"Missing required field=SchemaField\(MsgSeqNum|34,"
    ):
        schema.validate(dec_m)
