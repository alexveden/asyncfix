import pytest
from asyncfix import AsyncFIXClient
from unittest.mock import patch, MagicMock, AsyncMock
from asyncfix.protocol import FIXProtocol44

def test_init():
    client = AsyncFIXClient()


