import asyncio
from unittest.mock import AsyncMock, MagicMock, patch

import pytest

from asyncfix import AsyncFIXDummyServer, ConnectionRole, ConnectionState, Journaler
from asyncfix.errors import FIXConnectionError
from asyncfix.protocol import FIXProtocol44


def test_init():
    log = MagicMock()
    j = Journaler()
    server = AsyncFIXDummyServer(
        FIXProtocol44(),
        "sender",
        "target",
        j,
        "local",
        777,
        heartbeat_period=12,
        logger=log,
    )

    assert isinstance(server.protocol, FIXProtocol44)
    assert server._session.sender_comp_id == "sender"
    assert server._session.target_comp_id == "target"
    assert server._journaler is j
    assert server._host == "local"
    assert server._port == 777
    assert server._heartbeat_period == 12
    assert server.log is log
    assert server.connection_role == ConnectionRole.ACCEPTOR


@pytest.mark.asyncio
async def test_connect():
    log = MagicMock()
    j = Journaler()
    server = AsyncFIXDummyServer(
        FIXProtocol44(),
        "sender",
        "target",
        j,
        "local",
        777,
        heartbeat_period=12,
        logger=log,
    )

    assert server.connection_state == ConnectionState.DISCONNECTED_NOCONN_TODAY
    with (
        patch("asyncio.start_server") as mock_start_server,
        patch("asyncfix.connection.AsyncFIXConnection.connect") as mock_base_connect,
        patch.object(server, "on_connect") as mock_on_connect,
    ):
        mock_srv = AsyncMock()
        mock_start_server.return_value = mock_srv

        await server.connect()

        assert mock_base_connect.await_count == 1
        assert not mock_on_connect.called
        assert server.connection_state == ConnectionState.DISCONNECTED_NOCONN_TODAY

        assert mock_start_server.await_count == 1
        assert len(mock_start_server.call_args[0]) == 3
        assert mock_start_server.call_args[0][1] == server._host
        assert mock_start_server.call_args[0][2] == server._port
        assert mock_start_server.call_args[1] == {}

        assert mock_srv.serve_forever.awaited

        reader = AsyncMock(asyncio.StreamReader)
        writer = AsyncMock(asyncio.StreamWriter)
        await server._handle_accept(reader, writer)
        assert not writer.close.called

        assert server.connection_state == ConnectionState.NETWORK_CONN_ESTABLISHED
        assert mock_on_connect.await_count == 1
        assert server._socket_writer == writer
        assert server._socket_reader == reader

        with pytest.raises(FIXConnectionError, match="Server already working"):
            await server.connect()

        await server._handle_accept(reader, writer)
        assert writer.close.call_count == 1
        assert writer.wait_closed.await_count == 1
