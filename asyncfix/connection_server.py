"""Dummy FIX server module."""
import asyncio
import logging

from asyncfix.connection import AsyncFIXConnection, ConnectionRole, ConnectionState
from asyncfix.errors import FIXConnectionError
from asyncfix.journaler import Journaler
from asyncfix.protocol import FIXProtocolBase


class AsyncFIXDummyServer(AsyncFIXConnection):
    """Simple server which supports only single connection (just for testing)."""

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
            sender_comp_id: server sender_comp_id tag
            target_comp_id: server target_comp_id tag
            journaler: message journaler
            host: fix host to listen
            port: fix port to bind
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
        self._connection_role = ConnectionRole.ACCEPTOR

    async def connect(self):
        """Starts the server and infinitely runs it.

        Raises:
            FIXConnectionError: when already connected
        """
        if self._socket_reader:
            raise FIXConnectionError("Server already working")

        # this must be called in order to launch socket_reader/heartbeat tasks
        await super().connect()

        server = await asyncio.start_server(self._handle_accept, self._host, self._port)
        async with server:
            await server.serve_forever()

    async def _handle_accept(
        self,
        reader: asyncio.StreamReader,
        writer: asyncio.StreamWriter,
    ):
        """Executed when new client connection established."""
        if self._socket_writer:
            self.log.info("Multiple connections are not allowed for dummy server")

            writer.close()
            await writer.wait_closed()

        self._socket_reader = reader
        self._socket_writer = writer
        self._connection_state = ConnectionState.NETWORK_CONN_ESTABLISHED
        addr = writer.get_extra_info("peername")
        self.log.info("Connection from %s" % repr(addr))

        await self.on_connect()
