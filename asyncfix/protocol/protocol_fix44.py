from asyncfix.message import FIXMessage
from asyncfix.protocol.protocol_base import FIXProtocolBase

from . import FMsgType, FTag


class FIXProtocol44(FIXProtocolBase):
    beginstring = "FIX.4.4"

    session_message_types = {
        FMsgType.HEARTBEAT,
        FMsgType.TESTREQUEST,
        FMsgType.RESENDREQUEST,
        FMsgType.REJECT,
        FMsgType.SEQUENCERESET,
        FMsgType.LOGOUT,
        FMsgType.LOGON,
        FMsgType.XMLNONFIX,
    }

    repeating_groups = {
        FTag.NoSecurityAltID: [FTag.SecurityAltID, FTag.SecurityAltIDSource],
        FTag.NoMiscFees: [
            FTag.MiscFeeAmt,
            FTag.MiscFeeCurr,
            FTag.MiscFeeType,
            FTag.MiscFeeBasis,
        ],
        FTag.NoClearingInstructions: [
            FTag.ClearingInstruction,
        ],
        FTag.NoEvents: [FTag.EventType, FTag.EventDate, FTag.EventPx, FTag.EventText],
        FTag.NoInstrAttrib: [FTag.InstrAttribType, FTag.InstrAttribValue],
        FTag.NoLegSecurityAltID: [FTag.LegSecurityAltID, FTag.LegSecurityAltIDSource],
        FTag.NoLegStipulations: [FTag.LegStipulationType, FTag.LegStipulationValue],
        FTag.NoNestedPartyIDs: [
            FTag.NestedPartyID,
            FTag.NestedPartyIDSource,
            FTag.NestedPartyRole,
            FTag.NoNestedPartySubIDs,
        ],
        FTag.NoNestedPartySubIDs: [FTag.NestedPartySubID, FTag.NestedPartySubIDType],
        FTag.NoNested2PartyIDs: [
            FTag.Nested2PartyID,
            FTag.Nested2PartyIDSource,
            FTag.Nested2PartyRole,
            FTag.NoNested2PartySubIDs,
        ],
        FTag.NoNested2PartySubIDs: [FTag.Nested2PartySubID, FTag.Nested2PartySubIDType],
        FTag.NoNested3PartyIDs: [
            FTag.Nested3PartyID,
            FTag.Nested3PartyIDSource,
            FTag.Nested3PartyRole,
            FTag.NoNested3PartySubIDs,
        ],
        FTag.NoNested3PartySubIDs: [FTag.Nested3PartySubID, FTag.Nested3PartySubIDType],
        FTag.NoPartyIDs: [
            FTag.PartyID,
            FTag.PartyIDSource,
            FTag.PartyRole,
            FTag.NoPartySubIDs,
        ],
        FTag.NoPartySubIDs: [FTag.PartySubID, FTag.PartySubIDType],
        FTag.NoPosAmt: [FTag.PosAmtType, FTag.PosAmt],
        FTag.NoPositions: [
            FTag.PosType,
            FTag.LongQty,
            FTag.ShortQty,
            FTag.PosQtyStatus,
        ],
        FTag.NoDlvyInst: [
            FTag.SettlInstSource,
            FTag.DlvyInstType,
            FTag.NoSettlPartyIDs,
        ],
        FTag.NoSettlPartyIDs: [
            FTag.SettlPartyID,
            FTag.SettlPartyIDSource,
            FTag.SettlPartyRole,
            FTag.NoSettlPartySubIDs,
        ],
        FTag.NoSettlPartySubIDs: [FTag.SettlPartySubID, FTag.SettlPartySubIDType],
        FTag.NoStipulations: [FTag.StipulationType, FTag.StipulationValue],
        FTag.NoTrdRegTimestamps: [
            FTag.TrdRegTimestamp,
            FTag.TrdRegTimestampType,
            FTag.TrdRegTimestampOrigin,
        ],
        FTag.NoUnderlyingSecurityAltID: [
            FTag.UnderlyingSecurityAltID,
            FTag.UnderlyingSecurityAltIDSource,
        ],
        FTag.NoUnderlyingStips: [FTag.UnderlyingStipType, FTag.UnderlyingStipValue],
        FTag.NoOrders: [
            FTag.ClOrdID,
            FTag.OrderID,
            FTag.SecondaryOrderID,
            FTag.SecondaryClOrdID,
            FTag.ListID,
            FTag.OrderQty,
            FTag.OrderAvgPx,
            FTag.OrderBookingQty,
        ],
        FTag.NoExecs: [
            FTag.LastQty,
            FTag.ExecID,
            FTag.SecondaryExecID,
            FTag.LastPx,
            FTag.LastParPx,
            FTag.LastCapacity,
        ],
        FTag.NoUnderlyings: [
            FTag.UnderlyingSymbol,
            FTag.UnderlyingSymbolSfx,
            FTag.UnderlyingSecurityID,
            FTag.UnderlyingSecurityIDSource,
            FTag.NoUnderlyingSecurityAltID,
            FTag.UnderlyingProduct,
            FTag.UnderlyingCFICode,
            FTag.UnderlyingSecurityType,
            FTag.UnderlyingSecuritySubType,
            FTag.UnderlyingMaturityMonthYear,
            FTag.UnderlyingMaturityDate,
            FTag.UnderlyingPutOrCall,
            FTag.UnderlyingCouponPaymentDate,
            FTag.UnderlyingIssueDate,
            FTag.UnderlyingRepoCollateralSecurityType,
            FTag.UnderlyingRepurchaseTerm,
            FTag.UnderlyingRepurchaseRate,
            FTag.UnderlyingFactor,
            FTag.UnderlyingCreditRating,
            FTag.UnderlyingInstrRegistry,
            FTag.UnderlyingCountryOfIssue,
            FTag.UnderlyingStateOrProvinceOfIssue,
            FTag.UnderlyingLocaleOfIssue,
            FTag.UnderlyingRedemptionDate,
            FTag.UnderlyingStrikePrice,
            FTag.UnderlyingStrikeCurrency,
            FTag.UnderlyingOptAttribute,
            FTag.UnderlyingContractMultiplier,
            FTag.UnderlyingCouponRate,
            FTag.UnderlyingSecurityExchange,
            FTag.UnderlyingIssuer,
            FTag.EncodedUnderlyingIssuerLen,
            FTag.EncodedUnderlyingIssuer,
            FTag.UnderlyingSecurityDesc,
            FTag.EncodedUnderlyingSecurityDescLen,
            FTag.EncodedUnderlyingSecurityDesc,
            FTag.UnderlyingCPProgram,
            FTag.UnderlyingCPRegType,
            FTag.UnderlyingCurrency,
            FTag.UnderlyingQty,
            FTag.UnderlyingPx,
            FTag.UnderlyingDirtyPrice,
            FTag.UnderlyingEndPrice,
            FTag.UnderlyingStartValue,
            FTag.UnderlyingCurrentValue,
            FTag.UnderlyingEndValue,
            FTag.NoUnderlyingStips,
        ],
        FTag.NoAllocs: [
            FTag.AllocAccount,
            FTag.AllocAcctIDSource,
            FTag.MatchStatus,
            FTag.AllocPrice,
            FTag.AllocQty,
            FTag.IndividualAllocID,
            FTag.ProcessCode,
            FTag.NoNestedPartyIDs,
            FTag.NotifyBrokerOfCredit,
            FTag.AllocHandlInst,
            FTag.AllocText,
            FTag.EncodedAllocTextLen,
            FTag.EncodedAllocText,
            FTag.Commission,
            FTag.CommType,
            FTag.CommCurrency,
            FTag.FundRenewWaiv,
            FTag.AllocAvgPx,
            FTag.AllocNetMoney,
            FTag.SettlCurrAmt,
            FTag.AllocSettlCurrAmt,
            FTag.SettlCurrency,
            FTag.AllocSettlCurrency,
            FTag.SettlCurrFxRate,
            FTag.SettlCurrFxRateCalc,
            FTag.AllocAccruedInterestAmt,
            FTag.AllocInterestAtMaturity,
            FTag.NoMiscFees,
            FTag.NoClearingInstructions,
            FTag.AllocSettlInstType,
            FTag.SettlDeliveryType,
            FTag.StandInstDbType,
            FTag.StandInstDbName,
            FTag.StandInstDbID,
            FTag.NoDlvyInst,
        ],
        FTag.NoLegs: [
            FTag.LegSymbol,
            FTag.LegSymbolSfx,
            FTag.LegSecurityID,
            FTag.LegSecurityIDSource,
            FTag.NoLegSecurityAltID,
            FTag.LegProduct,
            FTag.LegCFICode,
            FTag.LegSecurityType,
            FTag.LegSecuritySubType,
            FTag.LegMaturityMonthYear,
            FTag.LegMaturityDate,
            FTag.LegCouponPaymentDate,
            FTag.LegIssueDate,
            FTag.LegRepoCollateralSecurityType,
            FTag.LegRepurchaseTerm,
            FTag.LegRepurchaseRate,
            FTag.LegFactor,
            FTag.LegCreditRating,
            FTag.LegInstrRegistry,
            FTag.LegCountryOfIssue,
            FTag.LegStateOrProvinceOfIssue,
            FTag.LegLocaleOfIssue,
            FTag.LegRedemptionDate,
            FTag.LegStrikePrice,
            FTag.LegStrikeCurrency,
            FTag.LegOptAttribute,
            FTag.LegContractMultiplier,
            FTag.LegCouponRate,
            FTag.LegSecurityExchange,
            FTag.LegIssuer,
            FTag.EncodedIssuerLen,
            FTag.EncodedLegIssuer,
            FTag.LegSecurityDesc,
            FTag.EncodedLegSecurityDescLen,
            FTag.EncodedLegSecurityDesc,
            FTag.LegRatioQty,
            FTag.LegSide,
            FTag.LegCurrency,
            FTag.LegPool,
            FTag.LegDatedDate,
            FTag.LegContractSettlMonth,
            FTag.LegInterestAccrualDate,
        ],
    }

    def logon(self) -> FIXMessage:
        msg = FIXMessage(FMsgType.LOGON)
        msg.set(FTag.EncryptMethod, 0)
        msg.set(FTag.HeartBtInt, 30)
        return msg

    def logout(self) -> FIXMessage:
        msg = FIXMessage(FMsgType.LOGOUT)
        return msg

    def heartbeat(self) -> FIXMessage:
        msg = FIXMessage(FMsgType.HEARTBEAT)
        return msg

    def test_request(self) -> FIXMessage:
        msg = FIXMessage(FMsgType.TESTREQUEST)
        return msg

    def sequence_reset(self, responding_to, is_gap_fill) -> FIXMessage:
        msg = FIXMessage(FMsgType.SEQUENCERESET)
        msg.set(FTag.GapFillFlag, "Y" if is_gap_fill else "N")
        msg.set(FTag.MsgSeqNum, responding_to[FTag.BeginSeqNo])
        return msg

    def resend_request(self, begin_seq_no, end_seq_no="0") -> FIXMessage:
        msg = FIXMessage(FMsgType.RESENDREQUEST)
        msg.set(FTag.BeginSeqNo, str(begin_seq_no))
        msg.set(FTag.EndSeqNo, str(end_seq_no))
        return msg
