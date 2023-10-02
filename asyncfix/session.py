import logging

from asyncfix import FTag
from asyncfix.message import MessageDirection


class FIXSession:
    def __init__(self, key, target_comp_id, sender_comp_id):
        self.key = key
        self.sender_comp_id = sender_comp_id
        self.target_comp_id = target_comp_id

        self.next_num_out = None
        self.messages = None
        self.next_num_in = None

        self.reset_msgs()

    def __hash__(self):
        return hash((self.target_comp_id, self.sender_comp_id))

    def __eq__(self, o):
        if isinstance(o, FIXSession):
            return (
                self.target_comp_id == o.target_comp_id
                and self.sender_comp_id == o.sender_comp_id
            )
        elif isinstance(o, tuple):
            if len(o) != 2:
                return False
            return (self.target_comp_id == o[0] and self.sender_comp_id == o[1])
        return False

    def __repr__(self):
        return (
            f"FIXSession(key={self.key},"
            f" target={self.target_comp_id} sender={self.sender_comp_id} InSN={self.next_num_in} OutSN={self.next_num_out})" # noqa
        )

    def reset_msgs(self):
        self.next_num_out = 1
        self.next_num_in = 1
        self.messages = {MessageDirection.OUTBOUND: {}, MessageDirection.INBOUND: {}}

    def validate_comp_ids(self, target_comp_id, sender_comp_id):
        return (
            self.sender_comp_id == sender_comp_id
            and self.target_comp_id == target_comp_id
        )

    def allocate_snd_seq_no(self):
        n = str(self.next_num_out)
        self.next_num_out += 1
        return n

    def validate_recv_seq_no(self, seq_no):
        if self.next_num_in != int(seq_no):
            logging.warning(
                "SeqNum from client unexpected (Rcvd: %s Expected: %s)"
                % (seq_no, self.next_num_in)
            )
            return (False, self.next_num_in)
        else:
            return (True, seq_no)

    def reset_seq_num(self):
        self.next_num_out = 1
        self.next_num_in = 1

    def set_recv_seq_no(self, seq_no):
        self.next_num_in = int(seq_no) + 1

    def persist_msg(self, msg, direction):
        seqNo = msg[FTag.MsgSeqNum]
        self.messages[direction][seqNo] = msg
