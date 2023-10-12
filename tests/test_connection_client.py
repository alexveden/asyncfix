from unittest.mock import AsyncMock, MagicMock, patch

import pytest

from asyncfix import AsyncFIXClient, ConnectionRole, ConnectionState, Journaler
from asyncfix.errors import FIXConnectionError
from asyncfix.protocol import FIXProtocol44


def test_init():
    log = MagicMock()
    j = Journaler()
    client = AsyncFIXClient(
        FIXProtocol44(),
        "sender",
        "target",
        j,
        "local",
        777,
        heartbeat_period=12,
        logger=log,
    )

    assert isinstance(client.protocol, FIXProtocol44)
    assert client._session.sender_comp_id == "sender"
    assert client._session.target_comp_id == "target"
    assert client._journaler is j
    assert client._host == "local"
    assert client._port == 777
    assert client._heartbeat_period == 12
    assert client.log is log
    assert client.connection_role == ConnectionRole.INITIATOR


@pytest.mark.asyncio
async def test_connect():
    log = MagicMock()
    j = Journaler()
    client = AsyncFIXClient(
        FIXProtocol44(),
        "sender",
        "target",
        j,
        "local",
        777,
        heartbeat_period=12,
        logger=log,
    )

    assert client.connection_state == ConnectionState.DISCONNECTED_NOCONN_TODAY
    with (
        patch("asyncio.open_connection") as mock_open_connection,
        patch("asyncfix.connection.AsyncFIXConnection.connect") as mock_base_connect,
        patch.object(client, "on_connect") as mock_on_connect,
    ):
        mock_open_connection.return_value = ("r", "w")

        await client.connect()
        assert mock_base_connect.await_count == 1
        assert mock_open_connection.await_count == 1
        assert mock_open_connection.call_args[0] == ("local", 777)
        assert mock_open_connection.call_args[1] == {}
        assert client.connection_state == ConnectionState.NETWORK_CONN_ESTABLISHED
        assert client._socket_reader == "r"
        assert client._socket_writer == "w"

        assert mock_on_connect.awaited
        assert mock_on_connect.call_args[0] == ()
        assert mock_on_connect.call_args[1] == {}

        with pytest.raises(FIXConnectionError, match="Socket already connected"):
            await client.connect()


@pytest.mark.asyncio
async def test_connect_exception():
    log = MagicMock()
    j = Journaler()
    client = AsyncFIXClient(
        FIXProtocol44(),
        "sender",
        "target",
        j,
        "local",
        777,
        heartbeat_period=12,
        logger=log,
    )

    assert client.connection_state == ConnectionState.DISCONNECTED_NOCONN_TODAY
    with (
        patch("asyncio.open_connection") as mock_open_connection,
        patch("asyncfix.connection.AsyncFIXConnection.connect") as mock_base_connect,
        patch.object(client, "on_connect") as mock_on_connect,
    ):
        mock_open_connection.side_effect = ValueError

        await client.connect()
        assert mock_open_connection.await_count == 1
        assert client.connection_state == ConnectionState.DISCONNECTED_BROKEN_CONN
        assert client._socket_reader is None
        assert client._socket_writer is None

        assert mock_on_connect.await_count == 0
