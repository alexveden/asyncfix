from asyncfix import FIXMessage, FMsg, FTag


class FIXProtocolBase(object):
    beginstring: str = "FIXProtocolBase"
    repeating_groups: dict[str, list[str]] = {}
    session_message_types: set = set()
    fixtags: FTag = FTag
    msgtype: FMsg = FMsg

    def logon(self) -> FIXMessage:
        raise NotImplementedError("Implement this method in child class")

    def logout(self) -> FIXMessage:
        raise NotImplementedError("Implement this method in child class")

    def heartbeat(self) -> FIXMessage:
        raise NotImplementedError("Implement this method in child class")

    def test_request(self) -> FIXMessage:
        raise NotImplementedError("Implement this method in child class")

    def sequence_reset(self, new_seq_no: int, is_gap_fill: bool = False) -> FIXMessage:
        raise NotImplementedError("Implement this method in child class")

    def resend_request(self, begin_seq_no, end_seq_no="0") -> FIXMessage:
        raise NotImplementedError("Implement this method in child class")
