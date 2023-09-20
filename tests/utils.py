from asyncfix.message import FIXMessage


def assert_msg(msg: FIXMessage, tags: dict[int | str, str]):
    assert isinstance(msg, FIXMessage)
    assert tags, "you must set some tags"

    for t, v in tags.items():
        t = str(t)
        assert t in msg, f"Message missing tag={t}, msg={msg}"
        if msg[t] != str(v):
            raise AssertionError(
                f"Message tag={t} value {msg[t]} != expected value {str(v)}"
            )
