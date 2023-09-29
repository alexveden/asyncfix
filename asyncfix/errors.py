class FIXError(Exception):
    pass


class FIXMessageError(FIXError):
    pass


class FIXConnectionError(FIXError):
    pass


class DuplicateSeqNoError(FIXError):
    pass


class EncodingError(FIXError):
    pass


class DecodingError(FIXError):
    pass


class TagNotFoundError(FIXMessageError):
    pass


class DuplicatedTagError(FIXMessageError):
    pass


class RepeatingTagError(FIXMessageError):
    pass


class UnmappedRepeatedGrpError(FIXMessageError):
    pass
