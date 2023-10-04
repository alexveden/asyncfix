import datetime
import importlib
import unittest
from unittest.mock import Mock, patch

import pytest

from asyncfix import FMsg, FTag
from asyncfix.codec import Codec
from asyncfix.errors import (
    EncodingError,
    RepeatingTagError,
    TagNotFoundError,
    UnmappedRepeatedGrpError,
)
from asyncfix.message import FIXContainer, FIXMessage
from asyncfix.protocol import FIXProtocol44


class FakeDate(datetime.datetime):
    @classmethod
    def utcnow(cls):
        return cls(2015, 6, 19, 11, 8, 54)


@pytest.fixture
def fix_session():
    mock_session = Mock()
    mock_session.sender_comp_id = "sender"
    mock_session.target_comp_id = "target"
    mock_session.allocate_next_num_out.return_value = 1
    return mock_session


def test_decode():
    protocol = FIXProtocol44()
    codec = Codec(protocol)
    inMsg = (
        b"8=FIX.4.4\x019=817\x0135=J\x0134=953\x0149=FIX_ALAUDIT\x0156=BFUT_ALAUDIT\x0143=N\x0152=20150615-09:21:42.459\x0170=00000002664ASLO1001\x01626=2\x0110626=5\x0171=0\x0160=20150615-10:21:42\x01857=1\x0173=1\x0111=00000006321ORLO1\x0138=100.0\x01800=100.0\x01124=1\x0132=100.0\x0117=00000009758TRLO1\x0131=484.50\x0154=2\x0153=100.0\x0155=FTI\x01207=XEUE\x01454=1\x01455=EOM5\x01456=A\x01200=201506\x01541=20150619\x01461=FXXXXX\x016=484.50\x0174=2\x0175=20150615\x0178=2\x0179=TEST123\x0130009=12345\x01467=00000014901CALO1001\x019520=00000014898CALO1\x0180=33.0\x01366=484.50\x0181=0\x01153=484.50\x0110626=5\x0179=TEST124\x0130009=12345\x01467=00000014903CALO1001\x019520=00000014899CALO1\x0180=67.0\x01366=484.50\x0181=0\x01153=484.50\x0110626=5\x01453=3\x01448=TEST1\x01447=D\x01452=3\x01802=2\x01523=12345\x01803=3\x01523=TEST1\x01803=19\x01448=TEST1WA\x01447=D\x01452=38\x01802=4\x01523=Test1"
        b" Wait\x01803=10\x01523="
        b" \x01803=26\x01523=\x01803=3\x01523=TestWaCRF2\x01803=28\x01448=hagap\x01447=D\x01452=11\x01802=2\x01523=GB\x01803=25\x01523=BarCapFutures.FETService\x01803=24\x0110=033\x01"
    )
    msg, remaining, enc_msg = codec.decode(inMsg)

    exp_str = "8=FIX.4.4|9=817|35=J|34=953|49=FIX_ALAUDIT|56=BFUT_ALAUDIT|43=N|52=20150615-09:21:42.459|70=00000002664ASLO1001|626=2|10626=#err#|71=0|60=20150615-10:21:42|857=1|73=1=>[11=00000006321ORLO1|38=100.0|800=100.0]|124=1=>[32=100.0|17=00000009758TRLO1|31=484.50]|54=2|53=100.0|55=FTI|207=XEUE|454=1=>[455=EOM5|456=A]|200=201506|541=20150619|461=FXXXXX|6=484.50|74=2|75=20150615|78=1=>[79=TEST123]|30009=#err#|467=#err#|9520=#err#|80=#err#|366=#err#|81=#err#|153=#err#|79=TEST124|453=3=>[448=TEST1|447=D|452=3|802=2=>[523=12345|803=3, 523=TEST1|803=19], 448=TEST1WA|447=D|452=38|802=4=>[523=Test1 Wait|803=10, 523= |803=26, 523=|803=3, 523=TestWaCRF2|803=28], 448=hagap|447=D|452=11|802=2=>[523=GB|803=25, 523=BarCapFutures.FETService|803=24]]|10=033"  # noqa
    assert exp_str == str(msg)


def test_encode(fix_session):
    protocol = FIXProtocol44()
    codec = Codec(protocol)

    msg = FIXMessage(codec.protocol.msgtype.NEWORDERSINGLE)
    msg.set(codec.protocol.fixtags.Price, "123.45")
    msg.set(codec.protocol.fixtags.OrderQty, 9876)
    msg.set(codec.protocol.fixtags.Symbol, "VOD.L")
    msg.set(codec.protocol.fixtags.SecurityID, "GB00BH4HKS39")
    msg.set(codec.protocol.fixtags.SecurityIDSource, "4")
    msg.set(codec.protocol.fixtags.Account, "TEST")
    msg.set(codec.protocol.fixtags.HandlInst, "1")
    msg.set(codec.protocol.fixtags.ExDestination, "XLON")
    msg.set(codec.protocol.fixtags.Side, 1)
    msg.set(codec.protocol.fixtags.ClOrdID, "abcdefg")
    msg.set(codec.protocol.fixtags.Currency, "GBP")

    rptgrp1 = FIXContainer()
    rptgrp1.set("611", "aaa")
    rptgrp1.set("612", "bbb")
    rptgrp1.set("613", "ccc")

    msg.add_group("444", rptgrp1, 0)

    rptgrp2 = FIXContainer()
    rptgrp2.set("611", "zzz")
    rptgrp2.set("612", "yyy")
    rptgrp2.set("613", "xxx")
    msg.add_group("444", rptgrp2, 1)

    with patch("asyncfix.codec.datetime", FakeDate) as mock_date:
        result = codec.encode(msg, fix_session)
    expected = "8=FIX.4.4\x019=201\x0135=D\x0149=sender\x0156=target\x0134=1\x0152=20150619-11:08:54.000\x0144=123.45\x0138=9876\x0155=VOD.L\x0148=GB00BH4HKS39\x0122=4\x011=TEST\x0121=1\x01100=XLON\x0154=1\x0111=abcdefg\x0115=GBP\x01444=2\x01611=aaa\x01612=bbb\x01613=ccc\x01611=zzz\x01612=yyy\x01613=xxx\x0110=255\x01"
    assert expected == result


def test_decode_invalid_checksum(fix_session):
    protocol = FIXProtocol44()
    codec = Codec(protocol)

    msg = FIXMessage(codec.protocol.msgtype.NEWORDERSINGLE)
    msg.set(codec.protocol.fixtags.Price, "123.45")
    msg.set(codec.protocol.fixtags.OrderQty, 9876)
    msg.set(codec.protocol.fixtags.Symbol, "VOD.L")
    protocol = FIXProtocol44()
    codec = Codec(protocol)
    # enc_msg = codec.encode(msg, fix_session)
    # print(repr(enc_msg))
    # assert False, enc_msg

    enc_msg = b"8=FIX.4.4\x019=82\x0135=D\x0149=sender\x0156=target\x0134=1\x0152=20230919-07:13:26.808\x0144=123.45\x0138=9876\x0155=VOD.L\x0110=110\x01"  # noqa
    msg, parsed_len, raw_msg = codec.decode(enc_msg)

    assert msg is None
    assert parsed_len == len(enc_msg)

    with pytest.raises(AssertionError, match="invalid checksum tag"):
        msg, parsed_len, raw_msg = codec.decode(enc_msg, silent=False)


def test_decode_valid(fix_session):
    protocol = FIXProtocol44()
    codec = Codec(protocol)

    msg = FIXMessage(codec.protocol.msgtype.NEWORDERSINGLE)
    msg.set(codec.protocol.fixtags.Price, "123.45")
    msg.set(codec.protocol.fixtags.OrderQty, 9876)
    msg.set(codec.protocol.fixtags.Symbol, "VOD.L")
    protocol = FIXProtocol44()
    codec = Codec(protocol)
    # enc_msg = codec.encode(msg, fix_session)
    # print(repr(enc_msg))
    # assert False, enc_msg

    enc_msg = b"8=FIX.4.4\x019=82\x0135=D\x0149=sender\x0156=target\x0134=1\x0152=20230919-07:13:26.808\x0144=123.45\x0138=9876\x0155=VOD.L\x0110=100\x01"  # noqa
    msg, parsed_len, raw_msg = codec.decode(enc_msg, silent=False)

    assert isinstance(msg, FIXMessage)
    assert msg[8] == "FIX.4.4"
    assert msg.msg_type == FMsg.NEWORDERSINGLE
    assert isinstance(msg.msg_type, FMsg)
    assert msg[FTag.Price] == "123.45"
    assert msg[FTag.OrderQty] == "9876"
    assert msg[FTag.Symbol] == "VOD.L"
    assert parsed_len == len(enc_msg)
    assert raw_msg == enc_msg


def test_decode_invalid_no_fix(fix_session):
    protocol = FIXProtocol44()
    codec = Codec(protocol)

    enc_msg = b"my_some string without any "  # noqa
    msg, parsed_len, raw_msg = codec.decode(enc_msg)
    assert msg is None
    assert parsed_len == len(enc_msg)

    with pytest.raises(AssertionError, match="no fix header"):
        msg, parsed_len, raw_msg = codec.decode(enc_msg, silent=False)


def test_decode_invalid_with_added_fix(fix_session):
    protocol = FIXProtocol44()
    codec = Codec(protocol)

    enc_msg = b"somejunk\n8=FIX.4.4\x019=82\x0135=D\x0149=sender\x0156=target\x0134=1\x0152=20230919-07:13:26.808\x0144=123.45\x0138=9876\x0155=VOD.L\x0110=100\x01"  # noqa
    msg, parsed_len, raw_msg = codec.decode(enc_msg)
    assert isinstance(msg, FIXMessage)
    assert parsed_len == len(enc_msg)
    assert raw_msg == enc_msg[len(b"somejunk\n") :]

    msg, parsed_len, raw_msg = codec.decode(enc_msg, silent=False)


def test_decode_invalid_junk_with_incomplete_fix(fix_session):
    protocol = FIXProtocol44()
    codec = Codec(protocol)

    enc_msg = b"somejunk\n8=FIX.4.4\x019=82\x0135=D"  # noqa
    msg, parsed_len, raw_msg = codec.decode(enc_msg)
    # assert isinstance(msg, FIXMessage)
    assert msg is None
    assert parsed_len == len("somejunk\n")
    assert enc_msg[parsed_len:].startswith(b"8=FIX")

    with pytest.raises(AssertionError, match="incomplete message"):
        msg, parsed_len, raw_msg = codec.decode(enc_msg, silent=False)


def test_decode_invalid_2nd_fix_msg(fix_session):
    protocol = FIXProtocol44()
    codec = Codec(protocol)

    enc_msg = b"somejunk\n8=FIX.4.4\x019=82\x0135=D\x0149=sender\x0156=target\x0134=1\x0152=20230919-07:13:26.808\x0144=123.45\x0138=9876\x0155=VOD.L\x0110=100\x018=FIX.4.4\x019=82\x0135=D"  # noqa
    # msg, parsed_len, raw_msg = codec.decode(enc_msg)
    msg, parsed_len, raw_msg = codec.decode(enc_msg, silent=False)
    assert isinstance(msg, FIXMessage)
    assert parsed_len == len(
        b"somejunk\n8=FIX.4.4\x019=82\x0135=D\x0149=sender\x0156=target\x0134=1\x0152=20230919-07:13:26.808\x0144=123.45\x0138=9876\x0155=VOD.L\x0110=100\x01"
    )
    assert enc_msg[parsed_len:].startswith(b"8=FIX")


def test_decode_invalid_start_fix_msg(fix_session):
    protocol = FIXProtocol44()
    codec = Codec(protocol)

    enc_msg = b"35=D\x0149=sender\x0156=target\x0134=1\x018=FIX.4.4\x019=82\x0135=D\x0149=sender\x0156=target\x0134=1\x0152=20230919-07:13:26.808\x0144=123.45\x0138=9876\x0155=VOD.L\x0110=100\x01"  # noqa
    msg, parsed_len, raw_msg = codec.decode(enc_msg)
    assert isinstance(msg, FIXMessage)
    assert parsed_len == len(enc_msg)

    msg, parsed_len, raw_msg = codec.decode(enc_msg, silent=False)


def test_decode_groups(fix_session):
    protocol = FIXProtocol44()
    codec = Codec(protocol)

    msg_in = FIXMessage(codec.protocol.msgtype.NEWORDERSINGLE)
    msg_in.set(codec.protocol.fixtags.Price, "123.45")
    msg_in.set(codec.protocol.fixtags.OrderQty, 9876)
    msg_in.set(codec.protocol.fixtags.Symbol, "VOD.L")

    rptgrp1 = FIXContainer()
    rptgrp1.set(FTag.SecurityAltID, "abc")
    rptgrp1.set(FTag.SecurityAltIDSource, "bbb")
    msg_in.add_group(FTag.NoSecurityAltID, rptgrp1)

    rptgrp2 = FIXContainer()
    rptgrp2.set(FTag.SecurityAltID, "zzz")
    rptgrp2.set(FTag.SecurityAltIDSource, "xxx")
    msg_in.add_group(FTag.NoSecurityAltID, rptgrp2)

    g = FIXContainer()
    g.set("20323", "1")
    g.set("20324", "3")
    msg_in.add_group("20228", g)

    g = FIXContainer()
    g.set("20323", "1")
    g.set("20324", "3")
    msg_in.add_group("20228", g)

    protocol = FIXProtocol44()
    codec = Codec(protocol)
    enc_msg = codec.encode(msg_in, fix_session).encode()
    # print(repr(enc_msg))
    # assert False, enc_msg

    msg_out, parsed_len, raw_msg = codec.decode(enc_msg)

    assert isinstance(msg_out, FIXMessage)
    assert msg_out[8] == "FIX.4.4"
    assert msg_out.msg_type == FMsg.NEWORDERSINGLE
    assert msg_out[FTag.Price] == "123.45"
    assert msg_out[FTag.OrderQty] == "9876"
    assert msg_out[FTag.Symbol] == "VOD.L"

    # print(repr(msg_out))
    # assert False, enc_msg

    g = msg_out.get_group_list(FTag.NoSecurityAltID)
    assert g
    assert isinstance(g, list)
    assert len(g) == 2
    assert g[0][FTag.SecurityAltID] == "abc"
    assert g[0][FTag.SecurityAltIDSource] == "bbb"
    assert g[1][FTag.SecurityAltID] == "zzz"
    assert g[1][FTag.SecurityAltIDSource] == "xxx"

    with pytest.raises(RepeatingTagError, match="tag=.*was repeated"):
        msg_out["20323"]

    with pytest.raises(
        UnmappedRepeatedGrpError,
        match="tag exists, but it does not belong to any group",
    ):
        g = msg_out.get_group_list("20228")

    with pytest.raises(TagNotFoundError, match="missing tag group tag="):
        g = msg_out.get_group_list("129012099")


def test_decode_protocol_mismatch(fix_session):
    protocol = FIXProtocol44()
    codec = Codec(protocol)

    enc_msg = b"8=FIX.4.2\x019=82\x0135=D\x0149=sender\x0156=target\x0134=1\x0152=20230919-07:13:26.808\x0144=123.45\x0138=9876\x0155=VOD.L\x0110=100\x01"  # noqa
    msg, parsed_len, raw_msg = codec.decode(enc_msg)
    assert msg is None
    assert parsed_len == len(enc_msg)

    with pytest.raises(AssertionError, match="protocol beginstring mismatch"):
        msg, parsed_len, raw_msg = codec.decode(enc_msg, silent=False)


def test_decode_body_len_split_err(fix_session):
    protocol = FIXProtocol44()
    codec = Codec(protocol)

    # this is an error, but possibly caused by socket buffer not loaded
    #   expected to be appended by good data later
    enc_msg = b"8=FIX.4.4\x0199\x0199=2\x01"
    msg, parsed_len, raw_msg = codec.decode(enc_msg)
    assert msg is None
    assert parsed_len == len(enc_msg)

    with pytest.raises(AssertionError, match="BodyLength split error "):
        msg, parsed_len, raw_msg = codec.decode(enc_msg, silent=False)


def test_decode_bad_second_tag(fix_session):
    protocol = FIXProtocol44()
    codec = Codec(protocol)

    # this is an error, but possibly caused by socket buffer not loaded
    #   expected to be appended by good data later
    enc_msg = b"8=FIX.4.4\x0135=\x0199=2\x01"
    msg, parsed_len, raw_msg = codec.decode(enc_msg)
    assert msg is None
    assert parsed_len == 19

    with pytest.raises(AssertionError, match="2nd tag must be BodyLength"):
        msg, parsed_len, raw_msg = codec.decode(enc_msg, silent=False)


def test_decode_bad_second_tag_expected_body_length(fix_session):
    protocol = FIXProtocol44()
    codec = Codec(protocol)
    # 2nd tag always must be a bodylength
    enc_msg = b"8=FIX.4.4\x0135=8\x0199=2\x01"
    msg, parsed_len, raw_msg = codec.decode(enc_msg)
    assert msg is None
    assert parsed_len == len(enc_msg)

    with pytest.raises(AssertionError, match="2nd tag must be BodyLength"):
        msg, parsed_len, raw_msg = codec.decode(enc_msg, silent=False)


def test_decode_with_unicode_valid(fix_session):
    protocol = FIXProtocol44()
    codec = Codec(protocol)

    msg = FIXMessage(codec.protocol.msgtype.NEWORDERSINGLE)
    msg.set(codec.protocol.fixtags.Price, "123.45")
    msg.set(codec.protocol.fixtags.OrderQty, 9876)
    msg.set(codec.protocol.fixtags.Symbol, "ЮН")
    protocol = FIXProtocol44()
    codec = Codec(protocol)
    enc_msg = codec.encode(msg, fix_session).encode("cp1251")
    # print(repr(enc_msg))
    # assert False, enc_msg

    msg, parsed_len, raw_msg = codec.decode(enc_msg)
    assert msg is None
    assert parsed_len == len(enc_msg)

    with pytest.raises(AssertionError, match="invalid checksum tag"):
        msg, parsed_len, raw_msg = codec.decode(enc_msg, silent=False)


def test_decode_empty_tag(fix_session):
    protocol = FIXProtocol44()
    codec = Codec(protocol)

    enc_msg = b"8=FIX.4.4\x019=75\x0135=D\x0149=sender\x0156=target\x0134=1\x0152=20230919-07:13:26.808\x0144=123.45\x0138\x0155=VOD.L\x0110=100\x01"  # noqa
    msg, parsed_len, raw_msg = codec.decode(enc_msg)
    assert msg is None
    assert parsed_len == len(enc_msg)
    with pytest.raises(AssertionError, match="incomplete tag 38"):
        msg, parsed_len, raw_msg = codec.decode(enc_msg, silent=False)

    enc_msg = b"8=FIX.4.4\x019=75\x0135=D\x0149=sender\x0156=target\x0134=1\x0152=20230919-07:13:26.808\x0144=123.45\x01\x0155=VOD.L\x0110=100\x01"  # noqa
    msg, parsed_len, raw_msg = codec.decode(enc_msg)
    assert msg is None
    assert parsed_len == len(enc_msg)
    with pytest.raises(AssertionError, match="incomplete tag"):
        msg, parsed_len, raw_msg = codec.decode(enc_msg, silent=False)


def test_decode_minimum_message(fix_session):
    protocol = FIXProtocol44()
    codec = Codec(protocol)

    enc_msg = b"8=FIX.4.4\x019=75\x01"
    msg, parsed_len, raw_msg = codec.decode(enc_msg)
    assert msg is None
    assert parsed_len == 0
    with pytest.raises(AssertionError, match="Minimum message"):
        msg, parsed_len, raw_msg = codec.decode(enc_msg, silent=False)


def test_encode_decode_seqnum_reset_gap_fill(fix_session):
    protocol = FIXProtocol44()
    codec = Codec(protocol)

    msg = FIXMessage(
        FMsg.SEQUENCERESET,
        {FTag.GapFillFlag: "Y", FTag.MsgSeqNum: "3", 36: 7},
    )
    enc_msg = codec.encode(msg, fix_session)
    msg_dec, parsed_len, raw_msg = codec.decode(enc_msg.encode())

    assert msg_dec[34] == "3"
    assert msg_dec[FTag.GapFillFlag] == "Y"


def test_encode_decode_seqnum_reset_gap_fill_no(fix_session):
    protocol = FIXProtocol44()
    codec = Codec(protocol)

    msg = FIXMessage(
        FMsg.SEQUENCERESET,
        {FTag.MsgSeqNum: "3"},
    )
    enc_msg = codec.encode(msg, fix_session)
    msg_dec, parsed_len, raw_msg = codec.decode(enc_msg.encode())

    assert msg_dec[34] == "3"
    assert FTag.GapFillFlag not in msg_dec
    assert FTag.NewSeqNo not in msg_dec


def test_encode_decode_seqnum_reset_gap_fill_no_msgseqnum(fix_session):
    protocol = FIXProtocol44()
    codec = Codec(protocol)

    msg = FIXMessage(
        FMsg.SEQUENCERESET,
        {FTag.GapFillFlag: "Y", 36: 7},
    )
    with pytest.raises(
        EncodingError,
        match="SequenceReset must have the MsgSeqNum already populated",
    ):
        enc_msg = codec.encode(msg, fix_session)


def test_encode_decode_pos_dup_flag(fix_session):
    protocol = FIXProtocol44()
    codec = Codec(protocol)

    msg = FIXMessage(
        FMsg.ADVERTISEMENT,
        {FTag.PossDupFlag: "Y", 34: 7},
    )

    enc_msg = codec.encode(msg, fix_session)
    msg_dec, parsed_len, raw_msg = codec.decode(enc_msg.encode())

    assert msg_dec[34] == "7"
    assert msg_dec[FTag.PossDupFlag] == "Y"

    with pytest.raises(
        EncodingError,
        match="Failed to encode message with PossDupFlag=Y but no previous MsgSeqNum",
    ):
        msg = FIXMessage(
            FMsg.ADVERTISEMENT,
            {
                FTag.PossDupFlag: "Y",
            },
        )
        enc_msg = codec.encode(msg, fix_session)


def test_decode_custom_msg_type(fix_session):
    protocol = FIXProtocol44()
    codec = Codec(protocol)

    msg = FIXMessage(codec.protocol.msgtype.NEWORDERSINGLE)
    msg.set(codec.protocol.fixtags.Price, "123.45")
    msg.set(codec.protocol.fixtags.OrderQty, 9876)
    msg.set(codec.protocol.fixtags.Symbol, "VOD.L")
    protocol = FIXProtocol44()
    codec = Codec(protocol)
    # enc_msg = codec.encode(msg, fix_session)
    # print(repr(enc_msg))
    # assert False, enc_msg

    enc_msg = b"8=FIX.4.4\x019=82\x0135=ASD\x0149=sender\x0156=target\x0134=1\x0152=20230919-07:13:26.808\x0144=123.45\x0138=9876\x0155=VOD.L\x0110=248\x01"  # noqa
    msg, parsed_len, raw_msg = codec.decode(enc_msg, silent=False)
    assert msg.msg_type == "ASD"
