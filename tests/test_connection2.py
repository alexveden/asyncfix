import pytest
from asyncfix.connection import AsyncFIXConnection, ConnectionState
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
    connection.connection_state = ConnectionState.CONNECTED
    return connection


@pytest.mark.asyncio
async def test_connection_init(fix_connection):
    conn: AsyncFIXConnection = fix_connection
    ft = FIXTester(schema=FIX_SCHEMA, connection=conn)

    msg = conn.protocol.logon()
    await conn.send_msg(msg)

    assert ft.msent_count() == 1

    assert ft.msent_query((FTag.SenderCompID, FTag.TargetCompID)) == {
        FTag.SenderCompID: "SENDERTEST",
        FTag.TargetCompID: "TARGETTEST",
    }

    assert ft.msent_query((35, 34)) == {FTag.MsgType: FMsg.LOGON, "34": "1"}

    rmsg = await ft.reply(conn.protocol.logon())
    # FIX Tester.reply() - simulated server response (SenderCompID/TargetCompID swapped)
    assert rmsg.query(FTag.SenderCompID, FTag.TargetCompID) == {
        FTag.TargetCompID: "SENDERTEST",
        FTag.SenderCompID: "TARGETTEST",
    }
