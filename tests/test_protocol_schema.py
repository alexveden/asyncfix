import os
import xml.etree.ElementTree as ET
from unittest.mock import patch

import pytest

from asyncfix import FIXMessage, FMsg, FTag
from asyncfix.errors import FIXMessageError
from asyncfix.protocol.schema import (
    FIXSchema,
    SchemaComponent,
    SchemaField,
    SchemaGroup,
    SchemaMessage,
    SchemaSet,
)

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

    assert "ExecutionReport" in schema.messages


def test_xml_real_schema_tt():
    tree = ET.parse(os.path.join(TEST_DIR, "TT-FIX44.xml"))
    schema = FIXSchema(tree)

    assert len(schema.messages) == 40
    assert len(schema.components) == 0
    assert len(schema.field2tag) == 611

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
        match="Missing required field=SchemaField.*tag='37', name='OrderID',",
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
        match=(
            "msg field=SchemaField.*name='AdvSide'.*not allowed in"
            " SchemaMessage.*name=ExecutionReport"
        ),
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