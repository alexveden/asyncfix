# AsyncFIX Framework Examples

## Fix message management
```python
from asyncfix import FIXMessage, FTag, FMsg
from asyncfix.protocol import FOrdType

msg = FIXMessage(
    FMsg.NEWORDERSINGLE,
    {11: "clordis", "1": "account", FTag.Price: 21.21, FTag.OrderQty: 2},
)

# duplicate tag setting not allowed, needs replace
msg.set(FTag.Price, 22.22, replace=True)

# Can set by item
msg[FTag.Symbol] = 'TEST.SYM'

# Or integer tag
msg[40] = FOrdType.LIMIT

msg.set_group(
    FTag.NoAllocs,
    [{FTag.AllocID: 1, FTag.AllocAvgPx: 1}, {FTag.AllocID: 2, FTag.AllocAvgPx: 2}],
)

print(msg)
# > 11=clordis|1=account|44=22.22|38=2|55=TEST.SYM|40=2|78=2=>[70=1|153=1, 70=2|153=2]

print(repr(msg[40]))
# > '2'

print(msg.get_group_list(FTag.NoAllocs))
# > [70=1|153=1, 70=2|153=2]

print(msg.query(11, FTag.Price, "40"))
# > {<FTag.ClOrdID: '11'>: 'clordis', <FTag.Price: '44'>: '22.22', <FTag.OrdType: '40'>: '2'} # noqa
```

## FIX Validation by schema
```python

from asyncfix.protocol import FIXSchema
from asyncfix import FIXMessage, FMsg, FTag
from asyncfix.errors import FIXMessageError
import os

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

```

## Order Management and testing
```python

from asyncfix.protocol import (
    FIXNewOrderSingle,
    FOrdSide,
    FOrdStatus,
    FExecType,
)
from asyncfix import FIXTester

order = FIXNewOrderSingle(
    "clordTest", "US.F.TICKER", side=FOrdSide.BUY, price=200.0, qty=10
)

print("Send new")
print(order.new_req())
# > 11=clordTest--1|55=US.F.TICKER|1=000000|40=2|54=1|60=20231014-14:22:44.278|44=200.0|38=10


o = FIXNewOrderSingle(
    "clordTest", "US.F.TICKER", side=FOrdSide.BUY, price=200.0, qty=10
)

ft = FIXTester(schema=None)  # Optionally allows schema for validation
assert ft.order_register_single(o) == 1
assert o.status == FOrdStatus.CREATED, f"o.status={chr(o.status)}"

exep_rep_msg = ft.fix_exec_report_msg(
    o, o.clord_id, FExecType.PENDING_NEW, FOrdStatus.PENDING_NEW
)
print('FIXTester exec report')
print(exep_rep_msg)
# > 11=clordTest|37=1|17=10001|150=A|39=A|54=1|14=0.0|151=0.0|55=US.F.TICKER|44=200.0|38=10|6=0.0|1=000000


# Order processes exec report internally and maintains itself
assert o.process_execution_report(exep_rep_msg) == 1

```
