from __future__ import annotations
from typing import Any
from collections import OrderedDict
from asyncfix.protocol.msgtype import FMsgType
from enum import Enum


def isclass(cl):
    try:
        return issubclass(cl, cl)
    except TypeError:
        return False


class MessageDirection(Enum):
    INBOUND = 0
    OUTBOUND = 1


class FIXMessageError(Exception):
    pass


class TagNotFoundError(FIXMessageError):
    pass


class DuplicatedTagError(FIXMessageError):
    pass


class RepeatingTagError(FIXMessageError):
    pass


class UnmappedRepeatedGrpError(FIXMessageError):
    pass


class _FIXRepeatingGroupContainer:
    def __init__(self):
        self.groups: list[FIXContext] = []

    def add_group(self, group, index):
        if index == -1:
            self.groups.append(group)
        else:
            self.groups.insert(index, group)

    def remove_group(self, index):
        del self.groups[index]

    def get_group(self, index):
        return self.groups[index]

    def __str__(self):
        return str(len(self.groups)) + "=>" + str(self.groups)

    __repr__ = __str__


class FIXContext(object):
    def __init__(self, tags: dict[str | int, [str, float, int]] = None):
        self.tags: dict[str, str | _FIXRepeatingGroupContainer] = OrderedDict()

        if tags:
            for t, v in tags.items():
                self.set(t, v)

    def set(self, tag: str | int, value):
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
            if t in self.tags:
                raise DuplicatedTagError(f"tag={t} already exists")

            value = str(value)

        self.tags[t] = value

    def remove(self, tag: str | int):
        try:
            del self.tags[tag]
        except KeyError:
            pass

    def get(self, tag: str | int, default=TagNotFoundError):
        result = self.tags.get(str(tag), default)
        if result is TagNotFoundError:
            raise TagNotFoundError(f"tag={tag} not found in message")
        elif result is RepeatingTagError:
            raise RepeatingTagError(
                f"tag={tag} was repeated, possible undefined repeating group or"
                " malformed fix message"
            )
        return result

    def add_group(self, tag: str | int, group: FIXContext | dict, index: int = -1):
        tag = str(tag)

        if isinstance(group, dict):
            group = FIXContext(group)
        elif not isinstance(group, FIXContext):
            raise FIXMessageError(f'Expected FIXContext in group, got {type(group)}')

        if tag in self:
            group_container = self.tags[tag]
            group_container.add_group(group, index)
        else:
            group_container = _FIXRepeatingGroupContainer()
            group_container.add_group(group, index)
            self.tags[tag] = group_container

    def set_group(self, tag: str | int, groups: list[dict, FIXContext]):
        tag = str(tag)

        if tag in self:
            raise DuplicatedTagError(f"group with {tag=} already exists")

        group_container = _FIXRepeatingGroupContainer()

        for m in groups:
            if isinstance(m, dict):
                m = FIXContext(tags=m)
            elif not isinstance(m, FIXContext):
                raise ValueError(
                    f"groups must be a list of FIXContext or dict, got {type(m)}"
                )
            group_container.add_group(m, -1)

        self.tags[tag] = group_container

    def remove_group(self, tag: str | int, index=-1):
        tag = str(tag)
        if self.is_group(tag):
            try:
                if index == -1:
                    del self.tags[tag]
                    pass
                else:
                    groups = self.tags[tag]
                    groups.remove_group(index)
            except KeyError:
                pass

    def get_group(self, tag: str | int) -> list[FIXContext]:
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

    def get_group_by_tag(self, tag: str | int, gtag: str | int, gvalue) -> Any:
        for group in self.get_group(tag):
            if gtag in group.tags:
                if group.get(gtag) == gvalue:
                    return group
        raise TagNotFoundError(f"get_group_by_tag: {tag=} {gtag=} {gvalue=} missing")

    def get_group_by_index(self, tag: str | int, index: int) -> FIXContext:
        g = self.get_group(tag)

        if index >= len(g):
            raise TagNotFoundError(
                f"get_group_by_index: index is out of range of {tag=} group"
            )

        return g[index]

    def __getitem__(self, tag: str | int) -> Any:
        return self.get(tag)

    def __setitem__(self, tag: str | int, value):
        self.set(tag, value)

    def __delitem__(self, tag: str | int):
        del self.tags[str(tag)]

    def is_group(self, tag: str | int) -> bool | None:
        tag_val = self.get(tag, default=None)
        if tag_val is not None:
            if isinstance(tag_val, _FIXRepeatingGroupContainer):
                return True
            else:
                return False
        else:
            return None

    def __contains__(self, item: str | int):
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
        return self.__str__() == other.__str__()

    __repr__ = __str__


class FIXMessage(FIXContext):
    def __init__(
        self,
        msg_type: str | FMsgType,
        tags: dict[str | int, [str, float, int]] = None,
    ):
        self.msg_type = msg_type
        super().__init__(tags)

    def set_msg_type(self, msg_type: str | FMsgType):
        self.msg_type = msg_type
