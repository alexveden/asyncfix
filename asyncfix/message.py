from __future__ import annotations

from collections import OrderedDict
from enum import Enum
from typing import Any

from asyncfix import FMsg, FTag

from .errors import (
    DuplicatedTagError,
    FIXMessageError,
    RepeatingTagError,
    TagNotFoundError,
    UnmappedRepeatedGrpError,
)


def isclass(cl):
    try:
        return issubclass(cl, cl)
    except TypeError:
        return False


class MessageDirection(Enum):
    INBOUND = 0
    OUTBOUND = 1


class _FIXRepeatingGroupContainer:
    def __init__(self):
        self.groups: list[FIXContainer] = []

    def add_group(self, group, index):
        if index == -1:
            self.groups.append(group)
        else:
            self.groups.insert(index, group)

    def __str__(self):
        return str(len(self.groups)) + "=>" + str(self.groups)

    __repr__ = __str__


class FIXContainer(object):
    def __init__(
        self, tags: dict[str | int, [str, float, int, list[dict | FIXContainer]]] = None
    ):
        self.tags: dict[str, str | _FIXRepeatingGroupContainer] = OrderedDict()

        if tags:
            for t, v in tags.items():
                if isinstance(v, list):
                    self.set_group(t, v)
                else:
                    self.set(t, v)

    def set(self, tag: str | int, value, replace: bool = False):
        try:
            # tag also might be an FTag enum (so cast to str first)
            int(str(tag))
        except ValueError:
            raise FIXMessageError("Tags must be only integers")

        t = str(tag)

        if isclass(value):
            # Case for setting tags as errors (allow overwriting by Exception)
            value = value
        else:
            if not replace and t in self.tags:
                raise DuplicatedTagError(f"tag={t} already exists")

            value = str(value)

        self.tags[t] = value

    def get(self, tag: str | int, default=TagNotFoundError):
        result = self.tags.get(str(tag), default)
        if result is TagNotFoundError:
            raise TagNotFoundError(f"tag={tag} not found in message")
        elif result is RepeatingTagError:
            raise RepeatingTagError(
                f"tag={tag} was repeated, possible undefined repeating group or"
                " malformed fix message"
            )
        elif isinstance(result, _FIXRepeatingGroupContainer):
            raise FIXMessageError(
                "You are trying to get group as simple tag,use get_group*() methods"
            )
        return result

    def is_group(self, tag: str | int) -> bool | None:
        tag_val = self.tags.get(str(tag), None)
        if tag_val is not None:
            if isinstance(tag_val, _FIXRepeatingGroupContainer):
                return True
            else:
                return False
        else:
            return None

    def add_group(self, tag: str | int, group: FIXContainer | dict, index: int = -1):
        tag = str(tag)

        if isinstance(group, dict):
            group = FIXContainer(group)
        elif not isinstance(group, FIXContainer):
            raise FIXMessageError(f"Expected FIXContext in group, got {type(group)}")

        if tag in self:
            group_container = self.tags[tag]
            group_container.add_group(group, index)
        else:
            group_container = _FIXRepeatingGroupContainer()
            group_container.add_group(group, index)
            self.tags[tag] = group_container

    def set_group(self, tag: str | int, groups: list[dict, FIXContainer]):
        tag = str(tag)

        if tag in self:
            raise DuplicatedTagError(f"group with {tag=} already exists")

        group_container = _FIXRepeatingGroupContainer()

        for m in groups:
            if isinstance(m, dict):
                m = FIXContainer(tags=m)
            elif not isinstance(m, FIXContainer):
                raise FIXMessageError(
                    f"groups must be a list of FIXContext or dict, got {type(m)}"
                )
            group_container.add_group(m, -1)

        self.tags[tag] = group_container

    def get_group_list(self, tag: str | int) -> list[FIXContainer]:
        tag = str(tag)
        is_group = self.is_group(tag)
        if is_group is None:
            raise TagNotFoundError(f"missing tag group {tag=}")
        if not is_group:
            raise UnmappedRepeatedGrpError(
                "tag exists, but it does not belong to any group, not a group tag or"
                " missing `repeating_group` in protocol class"
            )
        return self.tags[tag].groups

    def get_group_by_tag(
        self, tag: str | int, gtag: str | int, gvalue: str
    ) -> FIXContainer:
        for group in self.get_group_list(tag):
            if gtag in group:
                if group.get(gtag) == gvalue:
                    return group
        raise TagNotFoundError(f"get_group_by_tag: {tag=} {gtag=} {gvalue=} missing")

    def get_group_by_index(self, tag: str | int, index: int) -> FIXContainer:
        g = self.get_group_list(tag)

        if index >= len(g):
            raise TagNotFoundError(
                f"get_group_by_index: index is out of range of {tag=} group"
            )

        return g[index]

    def query(self, *tags: tuple[FTag | str | int]) -> dict[FTag | str, str]:
        result = {}
        if not tags:
            tags = self.tags

        for t in tags:
            try:
                t = FTag(str(t))
            except Exception:
                t = str(int(t))

            result[t] = self.get(t, None)
        return result

    def items(self):
        return self.tags.items()

    def __getitem__(self, tag: str | int) -> Any:
        return self.get(tag)

    def __setitem__(self, tag: str | int, value):
        self.set(tag, value)

    def __delitem__(self, tag: str | int):
        del self.tags[str(tag)]

    def __contains__(self, item: str | int | dict[str, Any]):
        if isinstance(item, dict):
            assert item, "empty dict item"

            # tag member comparison
            for t, v in item.items():
                t = str(t)
                v = str(v)

                if t not in self.tags:
                    return False

                if self.is_group(t):
                    raise FIXMessageError(
                        "fix message __contains__ supports only simple tags, got group"
                        f" at tag={t}"
                    )

                if v != self.get(t):
                    return False
            return True
        else:
            return str(item) in self.tags

    def __str__(self):
        r = ""
        allTags = []
        for tag, tag_value in self.tags.items():
            if isclass(tag_value) and issubclass(tag_value, Exception):
                tag_value = "#err#"
            allTags.append("%s=%s" % (tag, tag_value))
        r += "|".join(allTags)
        return r

    def __eq__(self, other):
        # if our string representation looks the same, the objects are equivalent
        if isinstance(other, FIXContainer):
            return self.__str__() == other.__str__()
        elif isinstance(other, dict):
            ignore_tags = {
                FTag.BeginString,
                FTag.BodyLength,
                FTag.CheckSum,
                FTag.MsgType,
            }

            other_tags = set(
                [str(t) for t in other.keys() if str(t) not in ignore_tags]
            )
            self_tags = set(
                [str(t) for t in self.tags.keys() if str(t) not in ignore_tags]
            )

            if other_tags != self_tags:
                return False

            for t, v in other.items():
                if self.is_group(t):
                    raise FIXMessageError(
                        "fix message __eq__ (dict) supports only simple tags, got group"
                        f" at tag={t}"
                    )

                v = str(other[t])
                if v != self.get(t):
                    return False

            return True
        else:
            return False

    __repr__ = __str__


class FIXMessage(FIXContainer):
    def __init__(
        self,
        msg_type: str | FMsg,
        tags: dict[str | int, [str, float, int]] = None,
    ):
        self._msg_type = msg_type
        super().__init__(tags)

    @property
    def msg_type(self) -> str | FMsg:
        return self._msg_type

    @msg_type.setter
    def msg_type(self, msg_type: str | FMsg):
        self._msg_type = msg_type

    def __repr__(self):
        return f"msg_type={self.msg_type}|" + super().__str__()
