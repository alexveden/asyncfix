class FIXMessageError(Exception):
    pass


class TagNotFoundError(FIXMessageError):
    pass


class DuplicatedTagError(FIXMessageError):
    pass


class RepeatingTagError(FIXMessageError):
    pass


class UnmappedRepeatedGrpError(FIXMessageError):
    pass
