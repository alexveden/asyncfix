"""FIX Message encoding / decoding module."""

import logging
from datetime import datetime, timezone

from asyncfix import FMsg, FTag
from asyncfix.errors import EncodingError, InvalidTagError
from asyncfix.message import FIXContainer, FIXMessage, RepeatingTagError
from asyncfix.protocol import FIXProtocolBase
from asyncfix.session import FIXSession

MINIMUM_MSG_LENGTH = 3
TOKENS_LENGTH = 2


def _split_tag(
    tag: str,
    silent: bool = True,
    custom_error: str = "",
) -> tuple[str, str]:
    tokens = tag.split("=", 1)
    if len(tokens) != TOKENS_LENGTH:
        if custom_error:
            assert silent, f"{custom_error} {tag}"
        else:
            assert silent, f"incomplete tag {tag}"
        raise InvalidTagError
    return tokens[0], tokens[1]


class _RepeatingGroupContext(FIXContainer):
    def __init__(
        self,
        tag: str,
        repeating_group_tags: list[str],
        parent: FIXContainer,
    ) -> None:
        self.tag = tag
        self.repeating_group_tags = repeating_group_tags
        self.parent = parent
        FIXContainer.__init__(self)


class Codec:
    """Encoding / decoding engine.

    Attributes:
        protocol: FIX protocol
        SOH: encoded message separator

    """

    def __init__(self, protocol: FIXProtocolBase) -> None:
        """Codec init.

        Args:
            protocol: FIX protocol used in encoding/decoding

        """
        self.protocol: FIXProtocolBase = protocol
        self.SOH = "\x01"

    @staticmethod
    def current_datetime() -> str:
        """FIX complaint date-time string (UTC now)."""
        return datetime.now(timezone.utc).strftime("%Y%m%d-%H:%M:%S.%f")[:-3]

    def _add_tag(self, body: list[str], t: str, msg: FIXContainer) -> None:
        if msg.is_group(t):
            groups = msg.get_group_list(t)
            body.append(f"{t}={len(groups)}")
            for group in groups:
                for tag in group.tags:
                    self._add_tag(body, tag, group)
        else:
            body.append(f"{t}={msg[t]}")

    def encode(
        self,
        msg: FIXMessage,
        session: FIXSession,
        raw_seq_num: bool = False,
    ) -> str:
        """Encodes FIXMessage into serialized message.

        Args:
            msg: generic FIXMessage
            session: current session (for seq num)
            raw_seq_num: if True - uses MsgSeqNum from `msg`

        Returns:
            encoded message (string)

        Raises:
            EncodingError: when failed MsgSeqNum conditions for some types of messages

        """
        # Create body
        body = [
            f"{FTag.SenderCompID}={session.sender_comp_id}",
            f"{FTag.TargetCompID}={session.target_comp_id}",
        ]

        msg_type = msg.msg_type
        if raw_seq_num:
            seq_no = int(msg[FTag.MsgSeqNum])
        elif msg_type == FMsg.SEQUENCERESET:
            if FTag.MsgSeqNum not in msg:
                raise EncodingError(
                    "SequenceReset must have the MsgSeqNum already populated",
                )
            seq_no = int(msg[FTag.MsgSeqNum])
        elif msg.get(FTag.PossDupFlag, "N") == "Y":
            # if we have the PossDupFlag set, we need to send the message
            # with the same seqNo
            if FTag.MsgSeqNum not in msg:
                raise EncodingError(
                    "Failed to encode message with PossDupFlag=Y but no"
                    " previous MsgSeqNum",
                )
            seq_no = int(msg[FTag.MsgSeqNum])
        else:
            seq_no = session.allocate_next_num_out()

        body.append(f"{FTag.MsgSeqNum}={seq_no}")
        body.append(f"{FTag.SendingTime}={self.current_datetime()}")

        for t in msg.tags:
            if t in {
                FTag.MsgSeqNum,
                FTag.SendingTime,
                FTag.SenderCompID,
                FTag.TargetCompID,
            }:
                continue
            self._add_tag(body, t, msg)

        body_string = self.SOH.join(body) + self.SOH

        # Create header
        header = []
        msg_type_str = f"{FTag.MsgType}={msg_type}"
        header.append(f"{FTag.BeginString}={self.protocol.beginstring}")
        header.append(f"{FTag.BodyLength}={len(body_string) + len(msg_type_str) + 1}")
        header.append(msg_type_str)

        fix_msg = self.SOH.join(header) + self.SOH + body_string
        cksum = sum([ord(i) for i in fix_msg]) % 256
        fix_msg = fix_msg + f"{FTag.CheckSum}={cksum:03}"

        # print len(fixmsg)

        return fix_msg + self.SOH

    def decode(
        self,
        rawmsg: bytes,
        silent: bool = True,
    ) -> tuple[FIXMessage | None, int, bytes | None]:
        """Decodes message from socket.

        Args:
            rawmsg: message bytes
            silent: no errors raised, returns non

        Returns:
            if OK - (FIXMessage, bytes_processed, valid_raw_msg_bytes)
            if ERR - (None, n_bytes_skip, None)

        """
        valid_idx = rawmsg.find(b"8=FIX.")
        if valid_idx == -1:
            assert silent, "no fix header"
            return None, len(rawmsg), None

        parsed_length = valid_idx

        msg = rawmsg[valid_idx:].decode("latin-1")

        next_msg = msg[5:].find("8=FIX.")
        if next_msg != -1:
            # Next fix message added, but incomplete
            next_msg += 5
        else:
            next_msg = len(msg)

        encoded_msg = rawmsg[valid_idx : next_msg + valid_idx]

        msg_tokens = msg[:next_msg].split(self.SOH)
        if not msg_tokens[-1]:
            msg_tokens = msg_tokens[:-1]

        # at a minimum we require BeginString, BodyLength & Checksum
        if len(msg_tokens) < MINIMUM_MSG_LENGTH:
            assert silent, "Minimum message"
            return None, parsed_length, None

        try:
            tag, value = _split_tag(msg_tokens[0], silent)
        except InvalidTagError:
            return None, len(rawmsg), None
        if value != self.protocol.beginstring:
            logging.error(
                "FIX Version unexpected (Recv: %s Expected: %s)",
                value,
                self.protocol.beginstring,
            )
            assert silent, "protocol beginstring mismatch"
            return None, len(rawmsg), None

        try:
            tag, value = _split_tag(msg_tokens[1], silent, "BodyLength split error")
        except InvalidTagError:
            return None, len(rawmsg), None
        if tag != FTag.BodyLength:
            logging.error(
                "*** BodyLength missing or not 2nd field *** [%s]: %s",
                tag,
                msg_tokens,
            )
            assert silent, "2nd tag must be BodyLength"
            return None, len(rawmsg), None

        msg_length = len(msg_tokens[0]) + len(msg_tokens[1]) + len("10=000") + 3
        msg_length += int(value)
        # message looks incomplete
        if msg_length > len(rawmsg):
            assert silent, "incomplete message"
            return None, parsed_length, None

        checksum_passed = False
        parsed_length += msg_length

        decoded_msg = FIXMessage("UNKNOWN")
        repeating_groups: list[_RepeatingGroupContext] = []
        current_context: FIXContainer = decoded_msg

        for m in msg_tokens:
            try:
                tag, value = _split_tag(m, silent)
            except InvalidTagError:
                return None, len(rawmsg), None

            if tag == FTag.CheckSum:
                cheksum_base = self.SOH.join(msg_tokens[:-1])
                checksum = (sum([ord(i) for i in cheksum_base]) + 1) % 256

                if checksum != int(value):
                    logging.warning(
                        "\tCheckSum: %s (INVALID) expecting %s",
                        int(value),
                        checksum,
                    )
                    assert (
                        silent
                    ), f"invalid checksum tag[10]={value} expected: {checksum} {msg_tokens=}"
                    checksum_passed = False
                else:
                    checksum_passed = True
            elif tag == FTag.MsgType:
                try:
                    decoded_msg.msg_type = FMsg(value)
                except ValueError:
                    assert silent, f"Invalid msg_type {value}"
                    return None, len(rawmsg), None

            # found the start of a repeating group
            if tag in self.protocol.repeating_groups:
                # i.e. we are already in a repeating group
                while (
                    isinstance(current_context, _RepeatingGroupContext)
                    and repeating_groups
                    and tag not in current_context.repeating_group_tags
                ):
                    current_context.parent.add_group(
                        current_context.tag,
                        current_context,
                    )
                    current_context = current_context.parent
                    # pop the completed group off the stack
                    del repeating_groups[-1]

                ctx = _RepeatingGroupContext(
                    tag,
                    self.protocol.repeating_groups[tag],
                    current_context,
                )
                repeating_groups.append(ctx)
                current_context = ctx
            elif repeating_groups:
                # we have 1 or more repeating groups in progress
                #    & our tag isn't the start of a group
                while (
                    isinstance(current_context, _RepeatingGroupContext)
                    and repeating_groups
                    and tag not in current_context.repeating_group_tags
                ):
                    current_context.parent.add_group(
                        current_context.tag,
                        current_context,
                    )
                    current_context = current_context.parent
                    # pop the completed group off the stack
                    del repeating_groups[-1]

                if tag in current_context.tags and isinstance(current_context, _RepeatingGroupContext):
                    # if the repeating group already contains this field,
                    #     start the next
                    current_context.parent.add_group(
                        current_context.tag,
                        current_context,
                    )
                    ctx = _RepeatingGroupContext(
                        current_context.tag,
                        current_context.repeating_group_tags,
                        current_context.parent,
                    )
                    del repeating_groups[-1]
                    repeating_groups.append(ctx)
                    current_context = ctx

                # else add it to the current one
                current_context.set(tag, value)
            elif tag in decoded_msg:
                # Repeating tag found, possibly RepGrp not in protocol schema
                decoded_msg.set(tag, RepeatingTagError)
            else:
                # this isn't a repeating group field, so just add it normally
                decoded_msg.set(tag, value)

        if checksum_passed:
            return decoded_msg, parsed_length, encoded_msg
        assert silent, f"Checksum probably missing: {msg_tokens}"
        return None, parsed_length, None
