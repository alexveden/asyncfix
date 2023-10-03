from asyncfix import FMsg, FTag


class FIXProtocolBase(object):
    beginstring: str = "FIXProtocolBase"
    repeating_groups: dict[str, list[str]] = {}
    session_message_types: set = set()
    fixtags: FTag = FTag
    msgtype: FMsg = FMsg
