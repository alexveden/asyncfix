import pytest
from unittest.mock import patch
from asyncfix.connection import AsyncFIXConnection, ConnectionState, ConnectionRole
from asyncfix.errors import FIXConnectionError
from asyncfix.protocol import FIXSchema, FIXProtocol44
from asyncfix.protocol.fix_tester import FIXTester
from asyncfix.journaler import Journaler
from asyncfix.message import MessageDirection
from asyncfix import FTag, FIXMessage, FMsg
from asyncfix.protocol.order_single import FIXNewOrderSingle
import xml.etree.ElementTree as ET
import pytest_asyncio
import os
import logging

TEST_DIR = os.path.abspath(os.path.dirname(__file__))
fix44_schema = ET.parse(os.path.join(TEST_DIR, "FIX44.xml"))
FIX_SCHEMA = FIXSchema(fix44_schema)


@pytest_asyncio.fixture
async def fix_connection():
    log = logging.getLogger("asyncfix_test")
    log.setLevel(logging.DEBUG)
    j = Journaler()
    connection = AsyncFIXConnection(
        FIXProtocol44(),
        "INITIATOR",
        "ACCEPTOR",
        journaler=j,
        host="localhost",
        port="64444",
        heartbeat_period=30,
        start_tasks=False,
        logger=log,
    )
    connection.connection_state = ConnectionState.NETWORK_CONN_ESTABLISHED
    assert connection.connection_role == ConnectionRole.UNKNOWN
    return connection


@pytest.mark.asyncio
async def test_connection_send_not_connected_error(fix_connection):
    conn: AsyncFIXConnection = fix_connection
    ft = FIXTester(schema=FIX_SCHEMA, connection=conn)
    msg = ft.msg_logon()

    for state in [
        ConnectionState.DISCONNECTED_NOCONN_TODAY,
        ConnectionState.DISCONNECTED_BROKEN_CONN,
        ConnectionState.DISCONNECTED_WCONN_TODAY,
        ConnectionState.AWAITING_CONNECTION,
        ConnectionState.INITIATE_CONNECTION,
    ]:
        conn.connection_state = state
        with pytest.raises(
            FIXConnectionError,
            match="Connection must be established before sending any FIX message",
        ):
            await conn.send_msg(msg)


@pytest.mark.asyncio
async def test_connection_send_first_logon_sets_state(fix_connection):
    conn: AsyncFIXConnection = fix_connection
    ft = FIXTester(schema=FIX_SCHEMA, connection=conn)

    conn.connection_state = ConnectionState.NETWORK_CONN_ESTABLISHED
    msg = ft.msg_logon()
    await conn.send_msg(msg)
    assert conn.connection_state == ConnectionState.LOGON_INITIAL_SENT

    # This is not allowed until logon confirmation!
    with pytest.raises(
        FIXConnectionError,
        match=(
            r"Initiator is waiting for Logon\(\) response, you must not send any"
            r" additional messages before"
        ),
    ):
        await conn.send_msg(ft.msg_heartbeat())


@pytest.mark.asyncio
async def test_connection_send_first_must_be_logon(fix_connection):
    conn: AsyncFIXConnection = fix_connection
    ft = FIXTester(schema=FIX_SCHEMA, connection=conn)

    conn.connection_state = ConnectionState.NETWORK_CONN_ESTABLISHED
    msg = ft.msg_sequence_reset(1, 12)
    with pytest.raises(
        FIXConnectionError,
        match=(
            r"You must send first Logon\(35=A\)/Logout\(\) message immediately after"
            r" connection.*"
        ),
    ):
        await conn.send_msg(msg)

    assert conn.connection_state == ConnectionState.NETWORK_CONN_ESTABLISHED


@pytest.mark.asyncio
async def test_connection_logon_acceptor_logon(fix_connection):
    conn: AsyncFIXConnection = fix_connection
    ft = FIXTester(schema=FIX_SCHEMA, connection=conn)

    assert conn.connection_state == ConnectionState.NETWORK_CONN_ESTABLISHED
    rmsg = await ft.reply(ft.msg_logon())
    assert conn.connection_role == ConnectionRole.ACCEPTOR
    assert conn.connection_state == ConnectionState.ACTIVE


@pytest.mark.asyncio
async def test_connection_logon_acceptor_logon_first_message_expected(fix_connection):
    conn: AsyncFIXConnection = fix_connection
    ft = FIXTester(schema=FIX_SCHEMA, connection=conn)

    assert conn.connection_state == ConnectionState.NETWORK_CONN_ESTABLISHED
    msg_reset = ft.msg_sequence_reset(1, 2)
    rmsg = await ft.reply(msg_reset)
    assert conn.connection_state == ConnectionState.DISCONNECTED_BROKEN_CONN


@pytest.mark.asyncio
async def test_connection_logon_valid(fix_connection):
    conn: AsyncFIXConnection = fix_connection
    ft = FIXTester(schema=FIX_SCHEMA, connection=conn)

    msg = ft.msg_logon()
    await conn.send_msg(msg)
    assert conn.connection_role == ConnectionRole.INITIATOR
    assert conn.connection_state == ConnectionState.LOGON_INITIAL_SENT

    assert len(ft.initiator_sent) == 1

    assert ft.initiator_sent_query((FTag.SenderCompID, FTag.TargetCompID)) == {
        FTag.SenderCompID: "INITIATOR",
        FTag.TargetCompID: "ACCEPTOR",
    }

    assert ft.initiator_sent_query((35, 34)) == {FTag.MsgType: FMsg.LOGON, "34": "1"}

    rmsg = await ft.reply(ft.msg_logon())
    assert conn.connection_state == ConnectionState.ACTIVE
    # FIX Tester.reply() - simulated server response (SenderCompID/TargetCompID swapped)
    assert rmsg.query(FTag.SenderCompID, FTag.TargetCompID) == {
        FTag.TargetCompID: "INITIATOR",
        FTag.SenderCompID: "ACCEPTOR",
    }


@pytest.mark.asyncio
async def test_connection_logon_low_seq_num_by_initator(fix_connection):
    conn: AsyncFIXConnection = fix_connection
    ft = FIXTester(schema=FIX_SCHEMA, connection=conn)

    conn.session.next_num_out = 20
    ft.set_next_num(num_in=21)

    msg = ft.msg_logon()
    await conn.send_msg(msg)
    assert conn.connection_role == ConnectionRole.INITIATOR
    assert conn.connection_state == ConnectionState.LOGON_INITIAL_SENT

    assert len(ft.initiator_sent) == 1

    assert ft.initiator_sent_query((FTag.SenderCompID, FTag.TargetCompID)) == {
        FTag.SenderCompID: "INITIATOR",
        FTag.TargetCompID: "ACCEPTOR",
    }

    assert ft.initiator_sent_query((35, 34)) == {FTag.MsgType: FMsg.LOGON, "34": "20"}

    await ft.process_msg_acceptor()

    assert ft.conn_accept.connection_state == ConnectionState.DISCONNECTED_BROKEN_CONN
    assert conn.connection_state == ConnectionState.DISCONNECTED_BROKEN_CONN

    assert ft.acceptor_sent_query((35, 58)) == {
        FTag.MsgType: FMsg.LOGOUT,
        "58": "MsgSeqNum is too low, expected 21, got 20",
    }


@pytest.mark.asyncio
async def test_connection_logon_low_seq_num_by_acceptor(fix_connection):
    conn: AsyncFIXConnection = fix_connection
    ft = FIXTester(schema=FIX_SCHEMA, connection=conn)

    msg = ft.msg_logon()
    await conn.send_msg(msg)
    assert conn.connection_role == ConnectionRole.INITIATOR
    assert conn.connection_state == ConnectionState.LOGON_INITIAL_SENT

    assert len(ft.initiator_sent) == 1

    assert ft.initiator_sent_query((FTag.SenderCompID, FTag.TargetCompID)) == {
        FTag.SenderCompID: "INITIATOR",
        FTag.TargetCompID: "ACCEPTOR",
    }

    assert ft.initiator_sent_query((35, 34)) == {FTag.MsgType: FMsg.LOGON, "34": "1"}

    conn.session.next_num_in = 10
    ft.set_next_num(num_out=4)
    await ft.process_msg_acceptor()
    assert len(ft.initiator_sent) == 2
    assert len(ft.acceptor_sent) == 1
    assert ft.acceptor_sent_query((35, 34)) == {FTag.MsgType: FMsg.LOGON, "34": "4"}
    assert ft.initiator_sent_query((35, 58)) == {
        FTag.MsgType: FMsg.LOGOUT,
        "58": "MsgSeqNum is too low, expected 10, got 4",
    }

    assert ft.conn_accept.connection_state == ConnectionState.DISCONNECTED_WCONN_TODAY
    assert conn.connection_state == ConnectionState.DISCONNECTED_BROKEN_CONN


@pytest.mark.asyncio
async def test_connection_validation_missing_seqnum(fix_connection):
    conn: AsyncFIXConnection = fix_connection
    ft = FIXTester(schema=FIX_SCHEMA, connection=conn)

    msg = ft.msg_logon()
    await conn.send_msg(msg)
    msg_out = ft.initiator_sent[-1]

    del msg_out[34]
    assert ft.conn_accept._validate_intergity(msg_out) == "MsgSeqNum(34) tag is missing"


@pytest.mark.asyncio
async def test_connection_validation_seqnum_toolow(fix_connection):
    conn: AsyncFIXConnection = fix_connection
    ft = FIXTester(schema=FIX_SCHEMA, connection=conn)

    conn.session.next_num_out = 20

    msg = ft.msg_logon()
    await conn.send_msg(msg)
    msg_out = ft.initiator_sent[-1]
    ft.set_next_num(num_in=21)

    assert (
        ft.conn_accept._validate_intergity(msg_out)
        == "MsgSeqNum is too low, expected 21, got 20"
    )


@pytest.mark.asyncio
async def test_connection_validation_beginstring(fix_connection):
    conn: AsyncFIXConnection = fix_connection
    ft = FIXTester(schema=FIX_SCHEMA, connection=conn)

    msg = ft.msg_logon()
    await conn.send_msg(msg)
    msg_out = ft.initiator_sent[-1]
    msg_out.set(FTag.BeginString, "FIX4.8", replace=True)

    assert (
        ft.conn_accept._validate_intergity(msg_out)
        == "Protocol BeginString(8) mismatch, expected FIX.4.4, got FIX4.8"
    )


@pytest.mark.asyncio
async def test_connection_validation_no_target(fix_connection):
    conn: AsyncFIXConnection = fix_connection
    ft = FIXTester(schema=FIX_SCHEMA, connection=conn)

    msg = ft.msg_logon()
    await conn.send_msg(msg)
    msg_out = ft.initiator_sent[-1]
    del msg_out[FTag.TargetCompID]

    assert conn._validate_intergity(msg_out) is True


@pytest.mark.asyncio
async def test_connection_validation_no_sender(fix_connection):
    conn: AsyncFIXConnection = fix_connection
    ft = FIXTester(schema=FIX_SCHEMA, connection=conn)

    msg = ft.msg_logon()
    await conn.send_msg(msg)
    msg_out = ft.initiator_sent[-1]
    del msg_out[FTag.SenderCompID]

    assert conn._validate_intergity(msg_out) is True


@pytest.mark.asyncio
async def test_connection_validation_sender_mismatch(fix_connection):
    conn: AsyncFIXConnection = fix_connection
    ft = FIXTester(schema=FIX_SCHEMA, connection=conn)

    msg = ft.msg_logon()
    await conn.send_msg(msg)
    msg_out = ft.initiator_sent[-1]
    msg_out.set(FTag.SenderCompID, "as", replace=True)

    assert conn._validate_intergity(msg_out) == "TargetCompID / SenderCompID mismatch"


@pytest.mark.asyncio
async def test_connection_validation_target_mismatch(fix_connection):
    conn: AsyncFIXConnection = fix_connection
    ft = FIXTester(schema=FIX_SCHEMA, connection=conn)

    msg = ft.msg_logon()
    await conn.send_msg(msg)
    msg_out = ft.initiator_sent[-1]
    msg_out.set(FTag.TargetCompID, "as", replace=True)

    assert conn._validate_intergity(msg_out) == "TargetCompID / SenderCompID mismatch"


@pytest.mark.asyncio
async def test_connection__process_resend_req(fix_connection):
    conn: AsyncFIXConnection = fix_connection
    ft = FIXTester(schema=FIX_SCHEMA, connection=conn)

    conn.session.next_num_out = 10

    with patch.object(conn, "journaler") as mock__journaler:
        msgs = [
            FIXMessage(FMsg.LOGON),
            FIXMessage(FMsg.HEARTBEAT),
            FIXNewOrderSingle("test", "ticker", "1", 10, 10).new_req(),
            FIXMessage(FMsg.HEARTBEAT),
            FIXMessage(FMsg.TESTREQUEST),
            FIXMessage(FMsg.RESENDREQUEST),
            FIXMessage(FMsg.SEQUENCERESET, {34: 8}),
        ]
        enc_msg = [conn.codec.encode(m, conn.session).encode() for m in msgs]
        mock__journaler.recover_messages.return_value = enc_msg

        resend_req = FIXMessage(
            FMsg.RESENDREQUEST,
            {FTag.BeginSeqNo: 1, FTag.EndSeqNo: "0"},
        )
        conn.connection_state = ConnectionState.RESENDREQ_HANDLING
        await conn._process_resend(resend_req)
        conn.connection_state = ConnectionState.ACTIVE

        assert len(ft.initiator_sent) == 3
        assert ft.initiator_sent[0].query(35, 34, 36, 123) == {
            FTag.MsgType: str(FMsg.SEQUENCERESET),
            FTag.MsgSeqNum: "1",
            FTag.NewSeqNo: "12",
            FTag.GapFillFlag: "Y",
        }

        assert ft.initiator_sent[1].query(35, 34, FTag.PossDupFlag) == {
            FTag.MsgType: str(FMsg.NEWORDERSINGLE),
            FTag.MsgSeqNum: "12",
            FTag.PossDupFlag: "Y",
        }

        assert ft.initiator_sent[2].query(35, 34, 36, 123) == {
            FTag.MsgType: str(FMsg.SEQUENCERESET),
            FTag.MsgSeqNum: "13",
            FTag.NewSeqNo: "17",
            FTag.GapFillFlag: "Y",
        }


@pytest.mark.asyncio
async def test_sequence_reset_request__no_gap(fix_connection):
    conn: AsyncFIXConnection = fix_connection
    ft = FIXTester(schema=FIX_SCHEMA, connection=conn)

    msg = ft.msg_logon()
    await conn.send_msg(msg)
    await ft.process_msg_acceptor()

    assert ft.conn_accept.connection_state == ConnectionState.ACTIVE
    assert ft.conn_init.connection_state == ConnectionState.ACTIVE

    seqreset_msg = FIXMessage(
        FMsg.SEQUENCERESET,
        {FTag.NewSeqNo: 10, FTag.MsgSeqNum: conn.session.next_num_out},
    )
    await conn.send_msg(seqreset_msg)
    await ft.process_msg_acceptor()

    assert ft.conn_accept.session.next_num_in == 10


@pytest.mark.asyncio
async def test_sequence_reset_request__unexpected_gapfillflag(fix_connection):
    conn: AsyncFIXConnection = fix_connection
    ft = FIXTester(schema=FIX_SCHEMA, connection=conn)

    msg = ft.msg_logon()
    await conn.send_msg(msg)
    await ft.process_msg_acceptor()

    assert ft.conn_accept.connection_state == ConnectionState.ACTIVE
    assert ft.conn_init.connection_state == ConnectionState.ACTIVE

    seqreset_msg = FIXMessage(
        FMsg.SEQUENCERESET,
        {
            FTag.NewSeqNo: 10,
            FTag.MsgSeqNum: conn.session.next_num_out,
            FTag.GapFillFlag: "Y",
        },
    )
    await conn.send_msg(seqreset_msg)
    await ft.process_msg_acceptor()

    assert ft.conn_accept.session.next_num_in == 10


@pytest.mark.asyncio
async def test__finalize_message(fix_connection):
    conn: AsyncFIXConnection = fix_connection
    ft = FIXTester(schema=FIX_SCHEMA, connection=conn)

    msg = ft.msg_sequence_reset(1, 10, is_gap_fill=True)
    assert conn.message_last_time == 0

    with patch.object(conn, "journaler") as mock_journaler:
        await conn._finalize_message(msg, b"msg")
        assert conn.message_last_time > 0
        assert mock_journaler.persist_msg.called
        assert mock_journaler.persist_msg.call_args[0] == (
            b"msg",
            conn.session,
            MessageDirection.INBOUND,
        )
        assert mock_journaler.persist_msg.call_args[1] == {}
        assert conn.session.next_num_in == 10

    msg = ft.msg_sequence_reset(10, 15, is_gap_fill=True)
    del msg[FTag.NewSeqNo]
    assert conn.session.set_next_num_in(msg) == 0

    with patch.object(conn, "journaler") as mock_journaler:
        await conn._finalize_message(msg, b"msg")
        assert not mock_journaler.persist_msg.called
        assert conn.session.next_num_in == 10

    msg = ft.msg_logon()
    assert FTag.MsgSeqNum not in msg
    assert conn.session.set_next_num_in(msg) == 0

    with patch.object(conn, "journaler") as mock_journaler:
        await conn._finalize_message(msg, b"msg")
        assert not mock_journaler.persist_msg.called
        assert conn.session.next_num_in == 10

    msg = ft.msg_logon()
    msg[FTag.MsgSeqNum] = 100
    assert conn.session.set_next_num_in(msg) == -1

    with patch.object(conn, "journaler") as mock_journaler:
        await conn._finalize_message(msg, b"msg")
        assert not mock_journaler.persist_msg.called
        assert conn.session.next_num_in == 10


@pytest.mark.asyncio
async def test_connection_both_seqnum_mismach_bidirectional_resend_req(fix_connection):
    conn: AsyncFIXConnection = fix_connection
    ft = FIXTester(schema=FIX_SCHEMA, connection=conn)

    conn.session.next_num_out = 20
    conn.session.next_num_in = 25
    ft.set_next_num(num_in=15, num_out=30)

    msg = ft.msg_logon()
    await conn.send_msg(msg)
    await ft.process_msg_acceptor()
    assert ft.conn_init.connection_state == ConnectionState.ACTIVE
    assert ft.conn_accept.connection_state == ConnectionState.ACTIVE
