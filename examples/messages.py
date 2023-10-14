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
