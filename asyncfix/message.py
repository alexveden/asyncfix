"""FIX message and containers module."""
from __future__ import annotations

from collections import OrderedDict
from enum import Enum

from asyncfix import FMsg, FTag
from asyncfix.errors import (
    DuplicatedTagError,
    FIXMessageError,
    RepeatingTagError,
    TagNotFoundError,
    UnmappedRepeatedGrpError,
)


def _isclass(cl):
    try:
        return issubclass(cl, cl)
    except TypeError:
        return False


class MessageDirection(Enum):
    """Direction of the message INBOUND/OUTBOUND."""

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
    """Generic FIX container.

    Attributes:
        tags: fix tags of the container
    """

    def __init__(
        self,
        tags: dict[str | int, [str, float, int, list[dict | FIXContainer]]] = None,
    ):
        """Initialize.

        Examples:
            m = FIXContainer({
                1: "account",
                FTag.ClOrdID: 'my-clord',
                FTag.NoAllocs: [{312: 'grp1'}, {312: 'grp2'}],
            })

        Args:
            tags: add tags at initialization time (all keys / values converted to str!)
        """
        self.tags: dict[str, str | _FIXRepeatingGroupContainer] = OrderedDict()

        if tags:
            for t, v in tags.items():
                if isinstance(v, list):
                    self.set_group(t, v)
                else:
                    self.set(t, v)

    def set(self, tag: str | int, value, replace: bool = False):
        """Set tag value.

        Args:
            tag: tag to set
            value: value to set (converted to str!)
            replace: set True - to intentionally rewrite existing tag

        Raises:
            DuplicatedTagError: when trying to set existing tag
            FIXMessageError: tag value is not convertible to int
        """
        try:
            # tag also might be an FTag enum (so cast to str first)
            int(str(tag))
        except ValueError:
            raise FIXMessageError("Tags must be only integers")

        t = str(tag)

        if _isclass(value):
            # Case for setting tags as errors (allow overwriting by Exception)
            value = value
        else:
            if not replace and t in self.tags:
                raise DuplicatedTagError(f"tag={t} already exists")

            value = str(value)

        self.tags[t] = value

    def get(self, tag: str | int | FTag, default=TagNotFoundError) -> str:
        """Get tag value.

        Args:
            tag: tag to get
            default: default value or raises TagNotFoundError

        Returns:
            string value of the tag

        Raises:
            FIXMessageError: trying to get FIX message group by tag, use get_group()
            RepeatingTagError: tag was repeated in decoded message, probably msg group
            TagNotFoundError: tag was not found in message
        """
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
        """Check if tag is repeating group.

        Args:
            tag: tag to check

        Returns:
            None - if not found
            True - if repeating group
            False - simple tag
        """
        tag_val = self.tags.get(str(tag), None)
        if tag_val is not None:
            if isinstance(tag_val, _FIXRepeatingGroupContainer):
                return True
            else:
                return False
        else:
            return None

    def add_group(self, tag: str | int, group: FIXContainer | dict, index: int = -1):
        """Add repeating group item to fix message.

        Args:
            tag: tag of repeating group, typically contains `No`, e.g. FTag.NoAllocs
            group: group item (another FIXContainer) or dict[tag: value]
            index: where to insert new value, default: append

        Raises:
            FIXMessageError: incorrect group type/value
        """
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
        """Set repeating groups of the message.

        Args:
            tag: tag of repeating group, typically contains `No`, e.g. FTag.NoAllocs
            groups: group items list of  (another FIXContainer) or dict[tag: value]

        Raises:
            DuplicatedTagError: group with the same tag already exists
            FIXMessageError: incorrect group type/value
        """
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
        """Get all repeating groups of a tag.

        Args:
            tag: target tag

        Returns:
            list of repeating FIXContainers

        Raises:
            UnmappedRepeatedGrpError: repeating group is not handled by protocol class
            TagNotFoundError: tag not found
        """
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
        self,
        tag: str | int,
        gtag: str | int,
        gvalue: str,
    ) -> FIXContainer:
        """Get repeating group item by internal group tag value.

        Args:
            tag: repeating group tag
            gtag: inside group tag to filter by
            gvalue: expected group tag value

        Returns:
            FIXContainer of repeating group item

        Raises:
            TagNotFoundError: tag not found
        """
        for group in self.get_group_list(tag):
            if gtag in group:
                if group.get(gtag) == gvalue:
                    return group
        raise TagNotFoundError(f"get_group_by_tag: {tag=} {gtag=} {gvalue=} missing")

    def get_group_by_index(self, tag: str | int, index: int) -> FIXContainer:
        """Get repeating group item by index.

        Args:
            tag: repeating group tag
            index: repeating group item index

        Returns:
            FIXContainer

        Raises:
            TagNotFoundError: tag not found
        """
        g = self.get_group_list(tag)

        if index >= len(g):
            raise TagNotFoundError(
                f"get_group_by_index: index is out of range of {tag=} group"
            )

        return g[index]

    def query(self, *tags: tuple[FTag | str | int]) -> dict[FTag | str, str]:
        """Request multiple tags from FIXMessage as dictionary.

        Args:
            *tags: tags var arguments

        Returns:
            dict {tag: value, ...}
        """
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
        """All tags items iterator."""
        return self.tags.items()

    def __getitem__(self, tag: str | int) -> str:
        """Item getter by tag."""
        return self.get(tag)

    def __setitem__(self, tag: str | int, value):
        """Item setter by tag."""
        self.set(tag, value)

    def __delitem__(self, tag: str | int):
        """Deletes tag from message."""
        del self.tags[str(tag)]

    def __contains__(self, item: str | int):
        """Checks if container contains tags."""
        return str(item) in self.tags

    def __str__(self):
        """As string."""
        r = ""
        allTags = []
        for tag, tag_value in self.tags.items():
            if _isclass(tag_value) and issubclass(tag_value, Exception):
                tag_value = "#err#"
            allTags.append("%s=%s" % (tag, tag_value))
        r += "|".join(allTags)
        return r

    def __eq__(self, other: FIXContainer | dict) -> bool:
        """Equality checks.

        Args:
            other: if FIXContainer - strict comparison,
                   if dict - core tags compare (without header)

        Returns:
            boolean

        Raises:
            FIXMessageError: group comparison not supported
        """
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
    """Generic FIXMessage."""

    def __init__(
        self,
        msg_type: str | FMsg,
        tags: dict[str | int, [str, float, int]] = None,
    ):
        """Initialize.

        Args:
            msg_type: message type, must comply with FIXTag=35
            tags: initial tags values
        """
        self._msg_type = msg_type
        super().__init__(tags)

    @property
    def msg_type(self) -> str | FMsg:
        """Message type."""
        return self._msg_type

    @msg_type.setter
    def msg_type(self, msg_type: str | FMsg):
        """Message type setter.

        Args:
            msg_type: new message type
        """
        self._msg_type = msg_type

    def __repr__(self):
        """Repr."""
        return f"msg_type={self.msg_type}|" + super().__str__()
