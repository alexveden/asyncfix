"""FIX Schema validation module."""

from __future__ import annotations

import dataclasses
import datetime as dtm
import re
import warnings
import xml.etree.ElementTree as ET
from math import isfinite
from typing import TypeVar, cast

from asyncfix import FIXMessage, FTag
from asyncfix.errors import FIXMessageError
from asyncfix.message import FIXContainer


@dataclasses.dataclass
class SchemaField:
    """FIX Field schema."""

    tag: str
    name: str
    ftype: str
    values: dict[str, str] = dataclasses.field(default_factory=dict)

    def __hash__(self) -> int:
        """Hash by Field.name."""
        return hash(self.name)

    def __eq__(self, o: object) -> bool:
        """Equality by SchemaField.name or tag."""
        if isinstance(o, SchemaField):
            return self.name == o.name
        elif isinstance(o, (str, int)):
            try:
                return self.tag == str(int(o))
            except (ValueError, TypeError):
                return self.name == o
        else:
            return False

    def validate_value(self, value: str) -> bool:
        """Validate tag value based on schema settings.

        Args:
            value: tag value

        Returns: True - if passed

        Raises:
            FIXMessageError: raised if validation failed
        """
        assert isinstance(value, str), "value must be a string"
        assert value, "empty value"

        if self.values:
            if value not in self.values:
                raise FIXMessageError(
                    f"Field={self.name} value expected to be one of the"
                    f" {list(self.values.keys())}, got ({value=})"
                )
            return True
        else:
            t = self.ftype.upper()
            err = None
            if t == "INT":
                err = SchemaField._validate_value_number(value, int)
            elif t in ["SEQNUM", "NUMINGROUP"]:
                err = SchemaField._validate_value_number(
                    value,
                    int,
                    no_zero=True,
                    no_negative=True,
                )
            elif t == "DAYOFMONTH":
                err = SchemaField._validate_value_number(value, int, num_range=(1, 31))
            elif t in {"FLOAT", "QTY", "PRICE", "PRICEOFFSET", "AMT", "PERCENTAGE"}:
                err = SchemaField._validate_value_number(
                    value, float, no_nonfinite=True
                )
            elif t in {"STRING", "MULTIPLESTRINGVALUE"}:
                err = SchemaField._validate_value_str(value)
            elif t in {"CHAR"}:
                err = SchemaField._validate_value_str(value, max_len=1)
            elif t in {"BOOLEAN"}:
                err = SchemaField._validate_value_str(
                    value, max_len=1, subset={"Y", "N"}
                )
            elif t in {"COUNTRY"}:
                err = SchemaField._validate_value_str(value, max_len=2, alpha_num=True)
            elif t in {"CURRENCY"}:
                err = SchemaField._validate_value_str(value, max_len=3, alpha_num=True)
            elif t in {"EXCHANGE"}:
                err = SchemaField._validate_value_str(value, max_len=4, alpha_num=True)
            elif t in {"LOCALMKTDATE", "UTCDATEONLY"}:
                err = SchemaField._validate_value_datetime(value, "%Y%m%d")
            elif t in {"UTCTIMESTAMP"}:
                err = SchemaField._validate_value_datetime(value, "%Y%m%d-%H:%M:%S")
            elif t in {"UTCTIMEONLY"}:
                err = SchemaField._validate_value_datetime(value, "%H:%M:%S")
            elif t == "MONTHYEAR":
                err = SchemaField._validate_value_monthyear(value)
            elif t in {"DATA", "LENGTH"}:
                # just hoping the data is ok
                err = None
            else:
                warnings.warn(f"Unsupported datatype: {t} for field={self}")

            err = self._validate_special_cases(value, err)

            if err:
                raise FIXMessageError(f"{self} validation error (value={value}): {err}")

            return True

    def _validate_special_cases(self, value: str, prev_err: str | None) -> str | None:
        if self.tag == "16" and value == "0":
            # EndSeqNo
            prev_err = None
        return prev_err

    @staticmethod
    def _validate_value_datetime(value: str, format: str) -> str | None:
        if "." in value and "%S" in format and "%f" not in format:
            format = f"{format}.%f"

        try:
            dtm.datetime.strptime(value, format)
            return None  # all good
        except ValueError as exc:
            return str(exc)

    @staticmethod
    def _validate_value_monthyear(value: str) -> str | None:
        """Special case for MonthYear type.

        String representing month of a year. An optional day of the month can be
          appended or an optional week code.
        Valid formats:
        YYYYMM
        YYYYMMDD
        YYYYMMWW.

        Valid values:
        YYYY = 0000-9999; MM = 01-12; DD = 01-31;
        WW = w1, w2, w3, w4, w5.
        """
        if "w" in value:
            week = value[-2:]
            if week not in {"w1", "w2", "w3", "w4", "w5"}:
                return f"YYYYMMWW [ww must be in w1,w2,w3,w4,w5], got {week}"
            format = "%Y%m"
            value = value[:-2]
            if len(value) != 6:
                return "remainder YYYYMM invalid"
        else:
            if len(value) == 6:
                format = "%Y%m"
            else:
                format = "%Y%m%d"

        return SchemaField._validate_value_datetime(value, format)

    @staticmethod
    def _validate_value_str(
        value: str,
        max_len: int | None = None,
        subset: set[str] | None = None,
        alpha_num: bool = False,
    ) -> str | None:
        assert value
        assert type(value) is str
        if "\x01" in value:
            return "Value contains SOH char"
        if "=" in value:
            return "Value contains `=` char"

        if max_len and len(value) > max_len:
            return "max legth exceeded"
        if subset and value not in subset:
            return f"out of subset: {subset}"
        if alpha_num and re.search(r"\W+", value):
            return "value contains non alphanumeric letters"

        return None

    @staticmethod
    def _validate_value_number(
        value: str,
        num_type: type[int | float],
        no_zero: bool = False,
        no_negative: bool = False,
        no_nonfinite: bool = False,
        num_range: tuple[float, float] | None = None,
    ) -> str | None:
        assert value
        assert num_type in (int, float)

        try:
            v = num_type(value)
            if no_zero and v == 0:
                raise ValueError("zero value")
            if no_negative and v < 0:
                raise ValueError("negative value")
            if no_nonfinite and not isfinite(float(v)):
                raise ValueError("not isfinite number")
            if num_range and not (v >= num_range[0] and v <= num_range[1]):
                raise ValueError(f"out of range {num_range}")
            # all good
            return None
        except ValueError as exc:
            return str(exc)

    def __str__(self) -> str:
        """As string: name|tag."""
        return f"{self.name}|{self.tag}"

    def __repr__(self) -> str:
        """Repr."""
        return f"SchemaField({self!s}, type={self.ftype})"


class SchemaSet:
    """Generic schema set (base for component/group).

    Attributes:
        name: schema name
        field: schema field
        members: members
        required: required flag
    """

    def __init__(self, name: str, field: SchemaField | None = None):
        """Initialize.

        Args:
            name: name of abstract set
            field: field of abstract set

        Raises:
            ValueError: if not NUMINGROUP type or similar tag name
        """
        self.name: str = name
        # this is set for groups, with attached field
        self.field: SchemaField | None = field
        if field and not (
            ("No" in field.name or "Num" in field.name)
            and field.ftype in ["NUMINGROUP", "INT"]
        ):
            # warnings.warn('')
            raise ValueError(
                "SchemaSet expected to have group field with NUMINGROUP|INT type,"
                f" name contais No/Num, got {field}"
            )
        self.members: dict[SchemaField | SchemaSet, SchemaField | SchemaSet] = {}
        self.required: dict[SchemaField | SchemaSet, bool] = {}

    @property
    def tag(self) -> str:
        """Tag number of SchemaField.

        Returns:
            tag

        Raises:
            ValueError: raised then tag is not single field
        """
        if self.field:
            return self.field.tag
        else:
            raise ValueError(f"tag property is not supported for {self}")

    def keys(self) -> list[str]:
        """List of field names."""
        return [m.name for m in self.members]

    def add(self, field_or_set: SchemaField | SchemaSet, required: bool) -> None:
        """Add SchemaSet member.

        Args:
            field_or_set: field or SchemaSet
            required: required tag flag

        Raises:
            ValueError: unsupported field_or_set value
        """
        if isinstance(field_or_set, SchemaField):
            assert field_or_set not in self.members
        elif isinstance(field_or_set, SchemaSet):
            assert field_or_set.field, "field_or_set.field is empty, try to merge"
        else:
            raise ValueError(  # noqa: TRY004
                f"Unsupported field_or_set type, got {type(field_or_set)}"
            )

        self.members[field_or_set] = field_or_set
        self.required[field_or_set] = required

    def merge(self, comp: SchemaSet) -> None:
        """Merge SchemaSet with another.

        Args:
            comp: SchemaSet
        """
        assert isinstance(comp, SchemaSet)

        for field in comp.members:
            self.add(field, comp.required[field])

    def __hash__(self) -> int:
        """Hash by field.name."""
        if self.field:
            return hash(self.field)
        else:
            return hash(self.name)

    def __eq__(self, o: object) -> bool:
        """Equality."""
        if self.field:
            return self.field == o
        else:
            return self.name == o

    def __contains__(self, item: str | SchemaField | SchemaSet) -> bool:
        """Check if SchemaSet contains field or name.

        Args:
            item: SchemaField or name (str)

        Returns:
            boolean

        Raises:
            FIXMessageError: incorrect item value
        """
        try:
            int(str(item))
            raise FIXMessageError("item looks like tag, use name or SchemaField")
        except ValueError:
            return item in self.members

    def __getitem__(
        self, item: str | SchemaField | SchemaSet
    ) -> SchemaField | SchemaSet:
        """Get field item by SchemaField or name.

        Args:
            item: SchemaField or name (str)

        Returns:
            SchemaField | SchemaSet

        Raises:
            FIXMessageError: incorrect item value
        """
        try:
            int(str(item))
            raise FIXMessageError("item looks like tag, use name or SchemaField")
        except ValueError:
            return self.members[cast(SchemaField | SchemaSet, item)]


class SchemaGroup(SchemaSet):
    """SchemaGroup container.

    Attributes:
        field_required:
    """

    field: SchemaField

    def __init__(self, field: SchemaField, required: bool):
        """Initialize.

        Args:
            field: SchemaField of group
            required: required flag
        """
        super().__init__(field.name, field)
        self.field_required = required

    def validate_group(self, groups: list[FIXContainer]) -> None:
        """Validate values of all tags in group.

        Args:
            groups: list of repeating group items

        Raises:
            FIXMessageError: validation failed
        """
        tag_order = {f.tag: i for i, f in enumerate(self.members.values())}
        tag_fields = {f.tag: f for f in self.members.values()}

        for fmsg in groups:
            has_first_tag = False
            prev_tag = -1

            for t, v in fmsg.items():
                if t not in tag_order:
                    raise FIXMessageError(
                        f"fixmessage={groups} contains unsupported tag for {self}"
                    )
                ord_idx = tag_order[t]

                if ord_idx == 0:
                    has_first_tag = True
                if prev_tag > ord_idx:
                    raise FIXMessageError(
                        f"fixmessage={groups} incorrect tag order {self}"
                    )

                field = tag_fields[t]

                if isinstance(field, SchemaField):
                    assert isinstance(v, str), "value must be a string"
                    field.validate_value(v)
                else:
                    # Nested group!?
                    assert isinstance(field, SchemaGroup)
                    if not fmsg.is_group(t):
                        raise FIXMessageError(
                            f"fixmessage={groups}, tag={t} must be a group {self}"
                        )

                    # validate nested group
                    field.validate_group(fmsg.get_group_list(t))

                prev_tag = ord_idx

            if not has_first_tag:
                raise FIXMessageError(
                    f"fixmessage={groups} does not contain mandatory first tag {self}"
                )

            for sv in tag_fields.values():
                if sv.tag in fmsg or not self.required[sv]:
                    continue
                if isinstance(sv, SchemaField):
                    raise FIXMessageError(
                        f"fixmessage={groups} missing required field {sv!r}"
                    )
                assert isinstance(sv, SchemaGroup)
                raise FIXMessageError(
                    f"fixmessage={groups} missing required group {sv!r}"
                )

    def __repr__(self) -> str:
        """Repr."""
        members = [str(m) for m in self.members]
        return f"SchemaGroup({self.field.name}, {members})"


class SchemaComponent(SchemaSet):
    """SchemaComponent container."""

    def __init__(self, name: str):
        """Initialize.

        Args:
            name: component name
        """
        super().__init__(name)


class SchemaHeader(SchemaSet):
    """SchemaHeader container."""

    def __init__(self) -> None:
        """Initialize header."""
        super().__init__(name="Header")


class SchemaMessage(SchemaSet):
    """SchemaMessage container.

    Attributes:
        msg_type: msg_type value
        msg_cat: message category
    """

    def __init__(self, name: str, msg_type: str, msg_cat: str):
        """Initialize.

        Args:
            name: message name
            msg_type: message type
            msg_cat: message category
        """
        super().__init__(name)
        self.msg_type = msg_type
        self.msg_cat = msg_cat

    def __repr__(self) -> str:
        """Repr."""
        return (
            f"SchemaMessage(name={self.name}, type={self.msg_type}, cat={self.msg_cat})"
        )


_ComponentT = TypeVar("_ComponentT", bound=SchemaSet)


class FIXSchema:
    """FIX schema validator."""

    def __init__(self, xml_or_path: ET.ElementTree | str):
        """Initialize.

        Args:
            xml_or_path: path to xml or xml.etree.ElementTree

        Raises:
            ValueError:
        """
        tree = ET.parse(xml_or_path) if isinstance(xml_or_path, str) else xml_or_path

        self._tag2field: dict[str, SchemaField] = {}
        self._field2tag: dict[str, SchemaField] = {}
        self._header: SchemaHeader = SchemaHeader()
        self._components: dict[str, SchemaComponent] = {}
        self._messages: dict[str, SchemaMessage] = {}
        self._messages_types: dict[str, SchemaMessage] = {}
        self._types: set[str] = set()

        root = tree.getroot()
        assert root is not None
        self._parse(root)

    def _parse_msg_set(
        self, component: _ComponentT, element: ET.Element
    ) -> _ComponentT | None:
        has_circular_refs = False
        for val in element:
            assert val.tag in ["field", "group", "component"]

            if val.tag == "field":
                field = self._field2tag[val.attrib["name"]]
                component.add(field, val.attrib["required"].upper() == "Y")
            elif val.tag == "component":
                if val.attrib["name"] not in self._components:
                    # We have circular reference, component was referenced before
                    #    described in XML data, just skip and rerun later
                    has_circular_refs = True
                    continue
                ref_component = self._components[val.attrib["name"]]
                component.merge(ref_component)
            elif val.tag == "group":
                g = self._parse_group(val)
                if g is None:
                    # Group also refers to other component, postpone it
                    has_circular_refs = True
                    continue
                component.add(g, g.field_required)

        if has_circular_refs:
            return None
        else:
            return component

    def _parse_group(self, element: ET.Element) -> SchemaGroup | None:
        assert self._field2tag, "parse fields first!"
        assert element.tag == "group"

        el_name = element.attrib["name"]

        gfield = self._field2tag[el_name]
        group = self._parse_msg_set(
            SchemaGroup(gfield, element.attrib["required"].upper() == "Y"),
            element,
        )
        # assert group, f'group parse erorr, {element.attrib}'
        return group

    def _parse_component(self, element: ET.Element) -> SchemaComponent | None:
        assert self._field2tag, "parse fields first!"
        assert element.tag == "component"

        el_name = element.attrib["name"]

        assert el_name not in self._components, "Duplicate component name or double run"
        component = self._parse_msg_set(SchemaComponent(el_name), element)

        if component:
            self._components[el_name] = component
            return component
        else:
            return None

    def _parse_message(self, element: ET.Element) -> SchemaMessage | None:
        assert self._field2tag, "parse fields first!"
        assert element.tag == "message"

        el_name = element.attrib["name"]

        assert el_name not in self._messages, "Duplicate message?"

        message = self._parse_msg_set(
            SchemaMessage(
                el_name,
                msg_type=element.attrib["msgtype"],
                msg_cat=element.attrib["msgcat"],
            ),
            element,
        )
        assert message, "Message probably refers to circular refs in comp or groups"

        self._messages[el_name] = message
        self._messages_types[message.msg_type] = message
        return message

    def _parse_header(self, element: ET.Element) -> None:
        assert self._field2tag, "parse fields first!"
        assert element.tag == "header"

        self._header = cast(SchemaHeader, self._parse_msg_set(SchemaHeader(), element))

    def _parse_field(self, element: ET.Element) -> None:
        assert element.tag == "field"

        f = SchemaField(
            tag=element.attrib["number"],
            name=element.attrib["name"],
            ftype=element.attrib["type"],
        )
        if len(element) > 0:
            for val in element:
                assert val.tag == "value"
                f.values[val.attrib["enum"]] = val.attrib["description"]

        self._types.add(f.ftype)
        self._tag2field[f.tag] = f
        self._field2tag[f.name] = f

    def _parse(self, root: ET.Element) -> None:
        assert not self._field2tag, "already parsed"

        fields = root.find("fields")
        assert fields is not None
        for element in fields:
            self._parse_field(element)

        header = root.find("header")
        assert header is not None
        self._parse_header(header)

        components = root.find("components")
        assert components is not None
        all_components = [e for e in components]
        full_count = len(all_components)
        prev_cnt = len(all_components)
        while all_components:
            i = 0
            while i < len(all_components):
                if self._parse_component(all_components[i]):
                    # component was parsed
                    del all_components[i]
                else:
                    i += 1

            if all_components:
                if len(all_components) == prev_cnt:
                    failed_comp = [c.attrib["name"] for c in all_components]
                    raise RuntimeError(
                        "Failed to resolve component circular reference."
                        f"Failed components: {failed_comp}"
                    )
                else:
                    prev_cnt = len(all_components)
        assert full_count == len(self._components), "Component count mismatch"

        n_msg = 0
        messages = root.find("messages")
        assert messages is not None
        for element in messages:
            self._parse_message(element)
            n_msg += 1

        assert n_msg == len(self._messages), "Message count mismatch"

    def _validate_header(self, msg: FIXMessage) -> None:
        schema_fields = set()
        schema_msg = self._header
        for fname, req in schema_msg.required.items():
            f = schema_msg[fname]
            schema_fields.add(fname)

            if req and isinstance(f, SchemaField):
                if f.tag not in msg:
                    raise FIXMessageError(f"Missing required field={f!r}")
                f_val = msg[f.tag]
                f.validate_value(f_val)
            elif req and isinstance(f, SchemaGroup) and f.tag not in msg:
                raise FIXMessageError(f"Missing required group={f!r}")

    def validate(self, msg: FIXMessage) -> bool:
        """Validates generic FIXMessage based on schema.

        Args:
            msg: generic FIXMessage

        Returns:
            True - if ok

        Raises:
            FIXMessageError: raises on invalid message
        """
        if msg.msg_type not in self._messages_types:
            raise FIXMessageError(f"msg_type=`{msg.msg_type}` not in schema")

        schema_msg = self._messages_types[str(msg.msg_type)]

        schema_fields = set()
        for fname, req in schema_msg.required.items():
            f = schema_msg[fname]
            schema_fields.add(fname)

            if req and isinstance(f, SchemaField) and f.tag not in msg:
                raise FIXMessageError(f"Missing required field={f!r}")
            if req and isinstance(f, SchemaGroup) and f.tag not in msg:
                raise FIXMessageError(f"Missing required group={f!r}")

        if "8" in msg:
            self._validate_header(msg)

        for tag, val in msg.tags.items():
            if tag == "10":
                # TODO: check the checksum
                continue
            if tag not in self._tag2field:
                raise FIXMessageError(f"msg tag={tag} not in schema")
            field = self._tag2field[tag]

            if field in self._header:
                continue

            if field not in schema_msg:
                raise FIXMessageError(
                    f"msg field={field} is not allowed in {schema_msg}"
                )

            fschema = schema_msg[field]
            if isinstance(fschema, SchemaField):
                if msg.is_group(tag):
                    raise FIXMessageError(
                        f"msg tag={tag} val={val} must be a tag, got group"
                    )
                assert isinstance(val, str)
                fschema.validate_value(val)

            elif isinstance(fschema, SchemaGroup):
                if not msg.is_group(tag):
                    raise FIXMessageError(f"msg tag={tag} val={val} must be a group")
                fschema.validate_group(msg.get_group_list(tag))

        return True

    def __getitem__(self, item: int | str | FTag) -> SchemaField:
        """Get SchemaField by tag."""
        try:
            tag = str(int(str(item)))
            return self._tag2field[tag]
        except ValueError:
            return self._field2tag[str(item)]
