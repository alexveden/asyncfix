import os
import xml.etree.ElementTree as ET

import pytest

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
        ValueError, match="SchemaSet expected to have group field with NUMINGROUP type"
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

    assert "NoContraBrokers" in schema.groups

    # Check messages
    assert schema.messages
    m = schema.messages["ExecutionReport"]
    assert isinstance(m, SchemaMessage)
    assert m.msg_type == "8"
    assert m.msg_cat == "app"
    assert isinstance(m["NoPartyIDs"], SchemaGroup)

    # Ensure group ordered!
    g = schema.groups["NoContraBrokers"]
    assert isinstance(g, SchemaGroup)
    assert ["ContraBroker", "ContraTrader"] == [str(m.name) for m in g.members.keys()]


def test_xml_circular_init(fix_circular_invalid_xml):
    with pytest.raises(
        RuntimeError,
        match=(
            r"Failed to resolve component circular reference.Failed components:"
            r" \['ContraGrp'\]"
        ),
    ):
        schema = FIXSchema(fix_circular_invalid_xml)
