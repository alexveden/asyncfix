"""AsyncFIX errors module."""


class FIXError(Exception):
    """Generic AsyncFIX error."""


class FIXMessageError(FIXError):
    """FIXMessage related error."""


class FIXConnectionError(FIXError):
    """FIX connection or session error."""


class DuplicateSeqNoError(FIXError):
    """Journaler duplicated seq no written (critical error)."""


class EncodingError(FIXError):
    """Codec encoding/decoding error."""


class TagNotFoundError(FIXMessageError):
    """Requested Tag not present in message."""


class DuplicatedTagError(FIXMessageError):
    """Trying to set tag which is already exist."""


class RepeatingTagError(FIXMessageError):
    """Tag was repeated after decoding, indicates mishandled fix group."""


class UnmappedRepeatedGrpError(FIXMessageError):
    """Repeating group improperly set up by protocol."""
