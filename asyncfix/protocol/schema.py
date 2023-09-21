from __future__ import annotations

import dataclasses
import xml.etree.ElementTree as ET

from asyncfix import FIXMessage


@dataclasses.dataclass
class SchemaField:
    tag: str
    name: str
    ftype: str
    values: dict[str, str] = dataclasses.field(default_factory=dict)

    def __hash__(self):
        return hash(self.name)

    def __eq__(self, o):
        if isinstance(o, SchemaField):
            return self.name == o.name
        elif isinstance(o, (str, int)):
            try:
                return self.tag == str(int(o))
            except Exception:
                return self.name == o
        else:
            return False

    def validate_value(self, value: str) -> bool:
        # TODO: add type validation too
        assert isinstance(value, str), "value must be a string"
        if self.values:
            return value in self.values
        else:
            return True


class SchemaSet:
    def __init__(self, name: str, field: SchemaField | None = None):
        self.name: str = name
        self.field: SchemaField = field  # this is set for groups, with attached field
        if field:
            if field.ftype != "NUMINGROUP":
                raise ValueError(
                    "SchemaSet expected to have group field with NUMINGROUP type, got"
                    f" {field}"
                )
        self.members: dict[SchemaField | SchemaSet, SchemaField | SchemaSet] = {}
        self.required: dict[SchemaField | SchemaSet, bool] = {}

    def add(self, field_or_set: SchemaField | SchemaSet, required: bool):
        if isinstance(field_or_set, SchemaField):
            assert field_or_set not in self.members
        elif isinstance(field_or_set, SchemaSet):
            assert field_or_set.field, "field_or_set.field is empty, try to merge"
        else:
            raise ValueError(f"Unsupported field_or_set type, got {type(field_or_set)}")

        self.members[field_or_set] = field_or_set
        self.required[field_or_set] = required

    def merge(self, comp: SchemaSet):
        assert isinstance(comp, SchemaSet)

        for field, required in comp.members.items():
            self.add(field, comp.required[field])

    def __hash__(self):
        if self.field:
            return hash(self.field)
        else:
            return hash(self.name)

    def __eq__(self, o):
        if self.field:
            return self.field == o
        else:
            return self.name == o

    def __contains__(self, item):
        return item in self.members

    def __getitem__(self, item):
        return self.members[item]


class SchemaGroup(SchemaSet):
    def __init__(self, field: SchemaField, required: bool):
        assert (
            field.ftype == "NUMINGROUP"
        ), f"Group field must have NUMINGROUP type: {field}"

        super().__init__(field.name, field)
        self.field_required = required


class SchemaComponent(SchemaSet):
    def __init__(self, name: str):
        super().__init__(name)


class SchemaMessage(SchemaSet):
    def __init__(self, name: str, msg_type: str, msg_cat: str):
        super().__init__(name)
        self.msg_type = msg_type
        self.msg_cat = msg_cat


class FIXSchema:
    def __init__(self, xml: ET.ElementTree):
        assert isinstance(xml, ET.ElementTree)
        self.tag2field: dict[str, SchemaField] = {}
        self.field2tag: dict[str, SchemaField] = {}
        self.groups: dict[str, SchemaGroup] = {}
        self.components: dict[str, SchemaComponent] = {}
        self.messages: dict[str, SchemaMessage] = {}
        self.header = {}

        self._parse(xml.getroot())

    def _parse_msg_set(self, component, element):
        has_circular_refs = False
        assert len(element) > 0, "empty component"
        for val in element:
            assert val.tag in ["field", "group", "component"]

            if val.tag == "field":
                field = self.field2tag[val.attrib["name"]]
                component.add(field, val.attrib["required"].upper() == "Y")
            elif val.tag == "component":
                if val.attrib["name"] not in self.components:
                    # We have circular reference, component was referenced before
                    #    described in XML data, just skip and rerun later
                    has_circular_refs = True
                    continue
                ref_component = self.components[val.attrib["name"]]
                component.merge(ref_component)
            elif val.tag == "group":
                g = self._parse_group(val)
                if g is None:
                    # Group also refers to other component, postpone it
                    has_circular_refs = True
                    continue
                component.add(g, g.required)

        if has_circular_refs:
            return None
        else:
            return component

    def _parse_group(self, element: ET.Element) -> SchemaGroup | None:
        assert self.field2tag, "parse fields first!"
        assert element.tag == "group"

        el_name = element.attrib["name"]
        if el_name in self.groups:
            # Already exists
            return self.groups[el_name]

        gfield = self.field2tag[el_name]
        group = self._parse_msg_set(
            SchemaGroup(gfield, element.attrib["required"].upper() == "Y"),
            element,
        )
        if group:
            self.groups[el_name] = group
            return group
        else:
            return None

    def _parse_component(self, element: ET.Element) -> SchemaComponent | None:
        assert self.field2tag, "parse fields first!"
        assert element.tag == "component"

        el_name = element.attrib["name"]

        if el_name in self.components:
            return self.components[el_name]

        component = self._parse_msg_set(SchemaComponent(el_name), element)

        if component:
            self.components[el_name] = component
            return component
        else:
            return None

    def _parse_message(self, element: ET.Element) -> SchemaMessage | None:
        assert self.field2tag, "parse fields first!"
        assert element.tag == "message"

        el_name = element.attrib["name"]

        assert el_name not in self.messages, "Duplicate message?"

        message = self._parse_msg_set(
            SchemaMessage(
                el_name,
                msg_type=element.attrib["msgtype"],
                msg_cat=element.attrib["msgcat"],
            ),
            element,
        )

        if message:
            self.messages[el_name] = message
            return message
        else:
            return None

    def _parse_field(self, element: ET.Element):
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

        self.tag2field[f.tag] = f
        self.field2tag[f.name] = f

    def _parse(self, root: ET.Element):
        for element in root.find("fields"):
            self._parse_field(element)

        all_components = [e for e in root.find("components")]

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

        for element in root.find("messages"):
            self._parse_message(element)

    def validate(self, msg: FIXMessage):
        pass

    def generate_protocol_code(self, path: str):
        pass
