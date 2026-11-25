"""Base FIX protocol."""

from typing import ClassVar

from asyncfix import FMsg, FTag


class FIXProtocolBase:
    """Generic FIX protocol."""

    beginstring: str = "FIXProtocolBase"
    repeating_groups: ClassVar[dict[str, list[str]]] = {}
    session_message_types: ClassVar[set] = set()
    fixtags: type[FTag] = FTag
    msgtype: type[FMsg] = FMsg
