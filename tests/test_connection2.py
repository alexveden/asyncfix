import pytest
from asyncfix.connection import AsyncFIXConnection, ConnectionState, ConnectionRole
from asyncfix.errors import FIXConnectionError
from asyncfix.protocol import FIXSchema, FIXProtocol44
from asyncfix.protocol.fix_tester import FIXTester
from asyncfix.journaler import Journaler
from asyncfix import FTag, FIXMessage, FMsg
import xml.etree.ElementTree as ET
import pytest_asyncio
import os

TEST_DIR = os.path.abspath(os.path.dirname(__file__))
fix44_schema = ET.parse(os.path.join(TEST_DIR, "FIX44.xml"))
FIX_SCHEMA = FIXSchema(fix44_schema)


@pytest_asyncio.fixture
async def fix_connection():
    j = Journaler()
    connection = AsyncFIXConnection(
        FIXProtocol44(),
        "SENDERTEST",
        "TARGETTEST",
        journaler=j,
        host="localhost",
        port="64444",
        heartbeat_period=30,
        start_tasks=False,
    )
    connection.connection_state = ConnectionState.NETWORK_CONN_ESTABLISHED
    assert connection.connection_role == ConnectionRole.UNKNOWN
    return connection


@pytest.mark.asyncio
async def test_connection_send_not_connected_error(fix_connection):
    conn: AsyncFIXConnection = fix_connection
    ft = FIXTester(schema=FIX_SCHEMA, connection=conn)
    msg = conn.protocol.logon()

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
    msg = conn.protocol.logon()
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
        await conn.send_msg(conn.protocol.heartbeat())


@pytest.mark.asyncio
async def test_connection_send_first_must_be_logon(fix_connection):
    conn: AsyncFIXConnection = fix_connection
    ft = FIXTester(schema=FIX_SCHEMA, connection=conn)

    conn.connection_state = ConnectionState.NETWORK_CONN_ESTABLISHED
    msg = conn.protocol.sequence_reset(0)
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
    rmsg = await ft.reply(conn.protocol.logon())
    assert conn.connection_role == ConnectionRole.ACCEPTOR
    assert conn.connection_state == ConnectionState.ACTIVE


@pytest.mark.asyncio
async def test_connection_logon_acceptor_logon_first_message_expected(fix_connection):
    conn: AsyncFIXConnection = fix_connection
    ft = FIXTester(schema=FIX_SCHEMA, connection=conn)

    assert conn.connection_state == ConnectionState.NETWORK_CONN_ESTABLISHED
    rmsg = await ft.reply(conn.protocol.sequence_reset(39))
    assert conn.connection_state == ConnectionState.DISCONNECTED_BROKEN_CONN


@pytest.mark.asyncio
async def test_connection_logon_valid(fix_connection):
    conn: AsyncFIXConnection = fix_connection
    ft = FIXTester(schema=FIX_SCHEMA, connection=conn)

    msg = conn.protocol.logon()
    await conn.send_msg(msg)
    assert conn.connection_role == ConnectionRole.INITIATOR
    assert conn.connection_state == ConnectionState.LOGON_INITIAL_SENT

    assert ft.msg_out_count() == 1

    assert ft.msg_out_query((FTag.SenderCompID, FTag.TargetCompID)) == {
        FTag.SenderCompID: "SENDERTEST",
        FTag.TargetCompID: "TARGETTEST",
    }

    assert ft.msg_out_query((35, 34)) == {FTag.MsgType: FMsg.LOGON, "34": "1"}

    rmsg = await ft.reply(conn.protocol.logon())
    assert conn.connection_state == ConnectionState.ACTIVE
    # FIX Tester.reply() - simulated server response (SenderCompID/TargetCompID swapped)
    assert rmsg.query(FTag.SenderCompID, FTag.TargetCompID) == {
        FTag.TargetCompID: "SENDERTEST",
        FTag.SenderCompID: "TARGETTEST",
    }


@pytest.mark.asyncio
async def test_connection_logon_low_seq_num_by_initator(fix_connection):
    conn: AsyncFIXConnection = fix_connection
    ft = FIXTester(schema=FIX_SCHEMA, connection=conn)

    conn.session.next_num_out = 20
    ft.set_next_num(num_in=21)

    msg = conn.protocol.logon()
    await conn.send_msg(msg)
    assert conn.connection_role == ConnectionRole.INITIATOR
    assert conn.connection_state == ConnectionState.LOGON_INITIAL_SENT

    assert ft.msg_out_count() == 1

    assert ft.msg_out_query((FTag.SenderCompID, FTag.TargetCompID)) == {
        FTag.SenderCompID: "SENDERTEST",
        FTag.TargetCompID: "TARGETTEST",
    }

    assert ft.msg_out_query((35, 34)) == {FTag.MsgType: FMsg.LOGON, "34": "20"}

    await ft.process_msg_acceptor()

    assert ft.conn_accept.connection_state == ConnectionState.DISCONNECTED_BROKEN_CONN

    assert ft.msg_in_query((35, 58)) == {
        FTag.MsgType: FMsg.LOGOUT,
        "58": "MsgSeqNum is too low, expected 21, got 20",
    }


@pytest.mark.asyncio
async def test_connection_logon_low_seq_num_by_acceptor(fix_connection):
    conn: AsyncFIXConnection = fix_connection
    ft = FIXTester(schema=FIX_SCHEMA, connection=conn)

    msg = conn.protocol.logon()
    await conn.send_msg(msg)
    assert conn.connection_role == ConnectionRole.INITIATOR
    assert conn.connection_state == ConnectionState.LOGON_INITIAL_SENT

    assert ft.msg_out_count() == 1

    assert ft.msg_out_query((FTag.SenderCompID, FTag.TargetCompID)) == {
        FTag.SenderCompID: "SENDERTEST",
        FTag.TargetCompID: "TARGETTEST",
    }

    assert ft.msg_out_query((35, 34)) == {FTag.MsgType: FMsg.LOGON, "34": "1"}

    conn.session.next_num_in = 10
    ft.set_next_num(num_out=4)
    rmsg = await ft.reply(conn.protocol.logon())
    assert conn.connection_state == ConnectionState.DISCONNECTED_BROKEN_CONN

    assert ft.msg_out_query((35, 58)) == {
        FTag.MsgType: FMsg.LOGOUT,
        "58": "MsgSeqNum is too low, expected 10, got 4",
    }


@pytest.mark.asyncio
async def test_connection_validation_missing_seqnum(fix_connection):
    conn: AsyncFIXConnection = fix_connection
    ft = FIXTester(schema=FIX_SCHEMA, connection=conn)

    msg = conn.protocol.logon()
    await conn.send_msg(msg)
    msg_out = ft.msg_out[-1]

    del msg_out[34]
    assert ft.conn_accept._validate_intergity(msg_out) == "MsgSeqNum(34) tag is missing"


@pytest.mark.asyncio
async def test_connection_validation_seqnum_toolow(fix_connection):
    conn: AsyncFIXConnection = fix_connection
    ft = FIXTester(schema=FIX_SCHEMA, connection=conn)

    conn.session.next_num_out = 20

    msg = conn.protocol.logon()
    await conn.send_msg(msg)
    msg_out = ft.msg_out[-1]
    ft.set_next_num(num_in=21)

    assert (
        ft.conn_accept._validate_intergity(msg_out)
        == "MsgSeqNum is too low, expected 21, got 20"
    )


@pytest.mark.asyncio
async def test_connection_validation_beginstring(fix_connection):
    conn: AsyncFIXConnection = fix_connection
    ft = FIXTester(schema=FIX_SCHEMA, connection=conn)

    msg = conn.protocol.logon()
    await conn.send_msg(msg)
    msg_out = ft.msg_out[-1]
    msg_out.set(FTag.BeginString, "FIX4.8", replace=True)

    assert (
        ft.conn_accept._validate_intergity(msg_out)
        == "Protocol BeginString(8) mismatch, expected FIX.4.4, got FIX4.8"
    )


@pytest.mark.asyncio
async def test_connection_validation_no_target(fix_connection):
    conn: AsyncFIXConnection = fix_connection
    ft = FIXTester(schema=FIX_SCHEMA, connection=conn)

    msg = conn.protocol.logon()
    await conn.send_msg(msg)
    msg_out = ft.msg_out[-1]
    del msg_out[FTag.TargetCompID]

    assert conn._validate_intergity(msg_out) is True


@pytest.mark.asyncio
async def test_connection_validation_no_sender(fix_connection):
    conn: AsyncFIXConnection = fix_connection
    ft = FIXTester(schema=FIX_SCHEMA, connection=conn)

    msg = conn.protocol.logon()
    await conn.send_msg(msg)
    msg_out = ft.msg_out[-1]
    del msg_out[FTag.SenderCompID]

    assert conn._validate_intergity(msg_out) is True


@pytest.mark.asyncio
async def test_connection_validation_sender_mismatch(fix_connection):
    conn: AsyncFIXConnection = fix_connection
    ft = FIXTester(schema=FIX_SCHEMA, connection=conn)

    msg = conn.protocol.logon()
    await conn.send_msg(msg)
    msg_out = ft.msg_out[-1]
    msg_out.set(FTag.SenderCompID, "as", replace=True)

    assert conn._validate_intergity(msg_out) == "TargetCompID / SenderCompID mismatch"


@pytest.mark.asyncio
async def test_connection_validation_target_mismatch(fix_connection):
    conn: AsyncFIXConnection = fix_connection
    ft = FIXTester(schema=FIX_SCHEMA, connection=conn)

    msg = conn.protocol.logon()
    await conn.send_msg(msg)
    msg_out = ft.msg_out[-1]
    msg_out.set(FTag.TargetCompID, "as", replace=True)

    assert conn._validate_intergity(msg_out) == "TargetCompID / SenderCompID mismatch"

