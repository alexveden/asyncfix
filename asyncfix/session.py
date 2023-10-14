"""FIXSession module."""
from asyncfix import FIXMessage, FMsg, FTag


class FIXSession:
    """Generic FIX Session container.

    Attributes:
        key: session DB id
        sender_comp_id: session sender
        target_comp_id: session target
        next_num_out: next expected seq num out
        next_num_in: next expected seq num in
    """
    def __init__(self, key, target_comp_id: str, sender_comp_id: str):
        """Initialize session.

        Args:
            key: session DB id
            target_comp_id: session target
            sender_comp_id: session sender
        """
        self.key = key
        """Session DB ID / key."""

        self.sender_comp_id = sender_comp_id
        self.target_comp_id = target_comp_id

        # Note: None is set intentionally, because session typically has to be
        #   loaded or created by Journaler class, therefore it sets session values
        #   internally
        self.next_num_out = None
        self.next_num_in = None

    def __hash__(self):
        """Hash by (target, sender)."""
        return hash((self.target_comp_id, self.sender_comp_id))

    def __eq__(self, o):
        """Equality by FIXSession or tuple(target, sender)."""
        if isinstance(o, FIXSession):
            return (
                self.target_comp_id == o.target_comp_id
                and self.sender_comp_id == o.sender_comp_id
            )
        elif isinstance(o, tuple):
            if len(o) != 2:
                return False
            return self.target_comp_id == o[0] and self.sender_comp_id == o[1]
        return False

    def __repr__(self):
        """Repr."""
        return (
            f"FIXSession(key={self.key},"
            f" target={self.target_comp_id} sender={self.sender_comp_id} InSN={self.next_num_in} OutSN={self.next_num_out})"  # noqa
        )

    def validate_comp_ids(self, target_comp_id: str, sender_comp_id: str) -> bool:
        """Ensure target_comp_id/sender_comp_id match.

        Args:
            target_comp_id: incoming target_comp_id
            sender_comp_id: incoming sender_comp_id

        Returns:
            bool
        """
        return (
            self.sender_comp_id == sender_comp_id
            and self.target_comp_id == target_comp_id
        )

    def allocate_next_num_out(self):
        """Increments next_num_out counter."""
        n = str(self.next_num_out)
        self.next_num_out += 1
        return n

    def set_next_num_in(self, msg: FIXMessage) -> int:
        """Sets next_num_in based on incoming FIXMessage.

        Args:
            msg: incoming message

        Returns:
            - if OK - current message seq_no
            - if ERROR - 0 or -1
        """
        if msg.msg_type == FMsg.SEQUENCERESET:
            if FTag.NewSeqNo not in msg:
                # Garbled message
                return 0
            seq_no = int(msg[FTag.NewSeqNo]) - 1

        else:
            if FTag.MsgSeqNum not in msg:
                # Garbled message
                return 0
            seq_no = int(msg[FTag.MsgSeqNum])

            if seq_no != self.next_num_in:
                # Gap detected
                return -1

        self.next_num_in = seq_no + 1

        return seq_no
