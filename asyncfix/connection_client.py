"""FIX Initiator (client) connection."""
import asyncio
import logging

from asyncfix.connection import AsyncFIXConnection, ConnectionRole, ConnectionState
from asyncfix.errors import FIXConnectionError
from asyncfix.journaler import Journaler
from asyncfix.protocol import FIXProtocolBase


class AsyncFIXClient(AsyncFIXConnection):
    """Generic FIX client."""
    def __init__(
        self,
        protocol: FIXProtocolBase,
        sender_comp_id: str,
        target_comp_id: str,
        journaler: Journaler,
        host: str,
        port: int,
        heartbeat_period: int = 30,
        logger: logging.Logger | None = None,
    ):
        """Initialization.

        Args:
            protocol: FIX protocol used in codec
            sender_comp_id: client sender_comp_id tag
            target_comp_id: client target_comp_id tag
            journaler: message journaler
            host: fix host
            port: fix port
            heartbeat_period: heartbeat_period in seconds
            logger: custom logger instance
        """
        super().__init__(
            protocol=protocol,
            sender_comp_id=sender_comp_id,
            target_comp_id=target_comp_id,
            journaler=journaler,
            host=host,
            port=port,
            heartbeat_period=heartbeat_period,
            logger=logger,
        )
        self._connection_role = ConnectionRole.INITIATOR

    async def connect(self):
        """Connects to the FIX server and initializes session.

        Raises:
            FIXConnectionError: if already connected
        """
        if self._socket_reader:
            raise FIXConnectionError("Socket already connected")

        # this must be called in order to launch socket_reader/heartbeat tasks
        await super().connect()

        try:
            self._socket_reader, self._socket_writer = await asyncio.open_connection(
                self._host, self._port
            )
        except Exception as exc:
            self.log.info(f"Connection error (waiting reconnect): {repr(exc)}")
            self._connection_state = ConnectionState.DISCONNECTED_BROKEN_CONN
        else:
            self._connection_state = ConnectionState.NETWORK_CONN_ESTABLISHED
            await self.on_connect()
