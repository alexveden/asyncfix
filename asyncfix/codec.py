import logging
from datetime import datetime

from asyncfix.message import FIXContainer, FIXMessage, RepeatingTagError
from asyncfix.protocol import FIXProtocolBase
from asyncfix.session import FIXSession


class EncodingError(Exception):
    pass


class DecodingError(Exception):
    pass


class RepeatingGroupContext(FIXContainer):
    def __init__(self, tag, repeating_group_tags, parent):
        self.tag = tag
        self.repeating_group_tags = repeating_group_tags
        self.parent = parent
        FIXContainer.__init__(self)


class Codec(object):
    def __init__(self, protocol: FIXProtocolBase):
        self.protocol: FIXProtocolBase = protocol
        self.SOH = "\x01"

    @staticmethod
    def current_datetime():
        return datetime.utcnow().strftime("%Y%m%d-%H:%M:%S.%f")[:-3]

    def _addTag(self, body, t, msg: FIXMessage):
        if msg.is_group(t):
            groups = msg.get_group_list(t)
            body.append("%s=%s" % (t, len(groups)))
            for group in groups:
                for tag in group.tags:
                    self._addTag(body, tag, group)
        else:
            body.append("%s=%s" % (t, msg[t]))

    def encode(self, msg: FIXMessage, session: FIXSession) -> str:
        # Create body
        body = []

        msg_type = msg.msg_type

        body.append(
            "%s=%s" % (self.protocol.fixtags.SenderCompID, session.sender_comp_id)
        )
        body.append(
            "%s=%s" % (self.protocol.fixtags.TargetCompID, session.target_comp_id)
        )

        seq_no = 0
        if msg_type == self.protocol.msgtype.SEQUENCERESET:
            if (
                self.protocol.fixtags.GapFillFlag in msg
                and msg[self.protocol.fixtags.GapFillFlag] == "Y"
            ):
                # in this case the sequence number should already be on the message
                try:
                    seq_no = msg[self.protocol.fixtags.MsgSeqNum]
                except KeyError:
                    raise EncodingError(
                        "SequenceReset with GapFill='Y' must have the MsgSeqNum already"
                        " populated"
                    )
            else:
                msg[self.protocol.fixtags.NewSeqNo] = session.allocate_snd_seq_no()
                seq_no = msg[self.protocol.fixtags.MsgSeqNum]
        else:
            # if we have the PossDupFlag set, we need to send the message
            #   with the same seqNo
            if (
                self.protocol.fixtags.PossDupFlag in msg
                and msg[self.protocol.fixtags.PossDupFlag] == "Y"
            ):
                try:
                    seq_no = msg[self.protocol.fixtags.MsgSeqNum]
                except KeyError:
                    raise EncodingError(
                        "Failed to encode message with PossDupFlay=Y but no previous"
                        " MsgSeqNum"
                    )
            else:
                seq_no = session.allocate_snd_seq_no()

        body.append("%s=%s" % (self.protocol.fixtags.MsgSeqNum, seq_no))
        body.append(
            "%s=%s" % (self.protocol.fixtags.SendingTime, self.current_datetime())
        )

        for t in msg.tags:
            self._addTag(body, t, msg)

        # Enable easy change when debugging
        SEP = self.SOH

        body = self.SOH.join(body) + self.SOH

        # Create header
        header = []
        msg_type = "%s=%s" % (self.protocol.fixtags.MsgType, msg_type)
        header.append(
            "%s=%s" % (self.protocol.fixtags.BeginString, self.protocol.beginstring)
        )
        header.append(
            "%s=%i" % (self.protocol.fixtags.BodyLength, len(body) + len(msg_type) + 1)
        )
        header.append(msg_type)

        fixmsg = self.SOH.join(header) + self.SOH + body

        cksum = sum([ord(i) for i in fixmsg]) % 256
        fixmsg = fixmsg + "%s=%0.3i" % (self.protocol.fixtags.CheckSum, cksum)

        # print len(fixmsg)

        return fixmsg + SEP

    def decode(self, rawmsg: bytes) -> tuple[FIXMessage | None, int]:
        parsed_length = 0
        try:
            valid_idx = rawmsg.find(b"8=FIX.")
            if valid_idx == -1:
                return None, len(rawmsg)

            rawmsg = rawmsg[valid_idx:].decode("utf-8")
            parsed_length = valid_idx
            msg = rawmsg.split(self.SOH)
            msg = msg[:-1]
        except UnicodeDecodeError as why:
            logging.error("Failed to parse message %s" % (why,))
            return (None, len(rawmsg))

        # at a minimum we require BeginString, BodyLength & Checksum
        if len(msg) < 3:
            return (None, parsed_length)

        toks = msg[0].split("=", 1)
        if len(toks) != 2:
            return (None, parsed_length)
        tag, value = toks

        if tag != self.protocol.fixtags.BeginString:
            logging.error("*** BeginString missing or not 1st field *** [" + tag + "]")
        elif value != self.protocol.beginstring:
            logging.error(
                "FIX Version unexpected (Recv: %s Expected: %s)"
                % (value, self.protocol.beginstring)
            )

        toks = msg[1].split("=", 1)
        if len(toks) != 2:
            return (None, parsed_length)
        tag, value = toks

        msg_length = len(msg[0]) + len(msg[1]) + len("10=000") + 3
        if tag != self.protocol.fixtags.BodyLength:
            logging.error("*** BodyLength missing or not 2nd field *** [" + tag + "]")
        else:
            msg_length += int(value)

        # message looks incomplete
        if msg_length > len(rawmsg):
            return (None, parsed_length)

        checksum_passed = False
        parsed_length += msg_length

        # resplit our message
        msg = rawmsg[:msg_length].split(self.SOH)
        msg = msg[:-1]
        decoded_msg = FIXMessage("UNKNOWN")
        repeating_groups = []
        repeating_group_tags = self.protocol.repeating_groups
        current_context = decoded_msg

        for m in msg:
            tag, value = m.split("=", 1)

            if tag == self.protocol.fixtags.CheckSum:
                cksum = (sum([ord(i) for i in list(self.SOH.join(msg[:-1]))]) + 1) % 256
                if cksum != int(value):
                    logging.warning(
                        "\tCheckSum: %s (INVALID) expecting %s" % (int(value), cksum)
                    )
                    checksum_passed = False
                else:
                    checksum_passed = True
            elif tag == self.protocol.fixtags.MsgType:
                try:
                    # self.protocol.msgtype.msgTypeToName(value)
                    decoded_msg.set_msg_type(value)
                except KeyError:
                    logging.error('*** MsgType "%s" not supported ***')

            # found the start of a repeating group
            if tag in repeating_group_tags:
                # i.e. we are already in a repeating group
                if type(current_context) is RepeatingGroupContext:
                    while (
                        repeating_groups
                        and tag not in current_context.repeating_group_tags
                    ):
                        current_context.parent.add_group(
                            current_context.tag, current_context
                        )
                        current_context = current_context.parent
                        # pop the completed group off the stack
                        del repeating_groups[-1]

                ctx = RepeatingGroupContext(
                    tag, repeating_group_tags[tag], current_context
                )
                repeating_groups.append(ctx)
                current_context = ctx
            elif repeating_groups:
                # we have 1 or more repeating groups in progress
                #    & our tag isn't the start of a group
                while (
                    repeating_groups and tag not in current_context.repeating_group_tags
                ):
                    current_context.parent.add_group(
                        current_context.tag, current_context
                    )
                    current_context = current_context.parent
                    # pop the completed group off the stack
                    del repeating_groups[-1]

                if tag in current_context.tags:
                    # if the repeating group already contains this field,
                    #     start the next
                    current_context.parent.add_group(
                        current_context.tag, current_context
                    )
                    ctx = RepeatingGroupContext(
                        current_context.tag,
                        current_context.repeating_group_tags,
                        current_context.parent,
                    )
                    del repeating_groups[-1]
                    repeating_groups.append(ctx)
                    current_context = ctx

                # else add it to the current one
                current_context.set(tag, value)
            else:
                if tag in decoded_msg:
                    # Repeating tag found, possibly RepGrp not in protocol schema
                    decoded_msg.set(tag, RepeatingTagError)
                else:
                    # this isn't a repeating group field, so just add it normally
                    decoded_msg.set(tag, value)

        if checksum_passed:
            return (decoded_msg, parsed_length)
        else:
            return (None, parsed_length)
