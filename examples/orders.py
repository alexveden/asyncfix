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
