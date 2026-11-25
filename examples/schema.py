"""FIX schema validation example."""

import os

from asyncfix import FIXMessage, FMsg, FTag
from asyncfix.errors import FIXMessageError
from asyncfix.protocol import FIXSchema

schema_file = os.path.abspath(
    os.path.join(os.path.dirname(__file__), "..", "tests", "FIX44.xml")
)
schema = FIXSchema(schema_file)

m = FIXMessage(FMsg.LOGON, {FTag.EncryptMethod: "0", FTag.HeartBtInt: 20})
# Passes!
assert schema.validate(m)

# Bad message
m = FIXMessage(FMsg.LOGON, {FTag.EncryptMethod: "0"})
try:
    schema.validate(m)
    assert False
except FIXMessageError as exc:
    print(f"Message validation failed: `{repr(m)}`: {repr(exc)}")
