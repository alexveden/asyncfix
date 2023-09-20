import asyncio
import unittest
from unittest.mock import AsyncMock, MagicMock, patch

from asyncfix.codec import Codec
from asyncfix.connection import FIXConnectionHandler
from asyncfix.engine import FIXEngine
from asyncfix.message import FIXContext, FIXMessage
from asyncfix.protocol import FIXProtocol44, FMsgType, FTag
from asyncfix.session import FIXSession

from .utils import assert_msg


class TestConnection(unittest.IsolatedAsyncioTestCase):
    def setUp(self):
        self.engine = FIXEngine()
        self.protocol = FIXProtocol44()
        self.codec = Codec(self.protocol)
        self.session = FIXSession("test", "test_target", "test_sender")

        self.socket_reader_mock = MagicMock()
        self.socket_reader_mock.read = AsyncMock()
        msg = FIXMessage(FMsgType.NEWORDERSINGLE)
        msg.set(FTag.Price, "123.45")
        msg.set(FTag.OrderQty, 9876)
        msg.set(FTag.Symbol, "VOD.L")
        self.msg = msg

    async def test_handle_read(self):
        self.socket_reader_mock.read.side_effect = [
            self.codec.encode(self.msg, self.session).encode(),
            self.codec.encode(self.msg, self.session).encode(),
            asyncio.CancelledError,  # This stops infinite loop
        ]

        h = FIXConnectionHandler(
            self.engine, self.protocol, self.socket_reader_mock, None
        )

        with patch.object(h, "process_message") as mock_process_message:
            await asyncio.wait_for(h.handle_read(), 1)

        self.assertEqual(mock_process_message.call_count, 2)

        for args in mock_process_message.call_args_list:
            self.assertEqual(len(args[0]), 1)  # 1 arg
            self.assertEqual(args[1], {})  # no kwargs

            assert_msg(
                args[0][0],
                {
                    FTag.Symbol: "VOD.L",
                    FTag.Price: "123.45",
                    FTag.OrderQty: "9876",
                },
            )

    async def test_handle_read_partial_msg(self):
        full = self.codec.encode(self.msg, self.session).encode()
        partial_1 = full[:20]
        partial_2 = full[20:]
        self.assertEqual((partial_1 + partial_2), full)

        self.socket_reader_mock.read.side_effect = [
            self.codec.encode(self.msg, self.session).encode(),
            partial_1,
            partial_2,
            asyncio.CancelledError,  # This stops infinite loop
        ]

        h = FIXConnectionHandler(
            self.engine, self.protocol, self.socket_reader_mock, None
        )

        with patch.object(h, "process_message") as mock_process_message:
            await asyncio.wait_for(h.handle_read(), 1)

        self.assertEqual(mock_process_message.call_count, 2)

        for args in mock_process_message.call_args_list:
            self.assertEqual(len(args[0]), 1)  # 1 arg
            self.assertEqual(args[1], {})  # no kwargs

            assert_msg(
                args[0][0],
                {
                    FTag.Symbol: "VOD.L",
                    FTag.Price: "123.45",
                    FTag.OrderQty: "9876",
                },
            )

    async def test_handle_read_partial_bad_data(self):
        full = self.codec.encode(self.msg, self.session).encode()
        partial_1 = full[:20]
        partial_2 = full[20:]
        self.assertEqual((partial_1 + partial_2), full)

        self.socket_reader_mock.read.side_effect = [
            self.codec.encode(self.msg, self.session).encode(),
            partial_1,
            partial_1,
            asyncio.CancelledError,  # This stops infinite loop
        ]

        h = FIXConnectionHandler(
            self.engine, self.protocol, self.socket_reader_mock, None
        )

        with patch.object(h, "process_message") as mock_process_message:
            await asyncio.wait_for(h.handle_read(), 1)

        self.assertEqual(mock_process_message.call_count, 1)

        for args in mock_process_message.call_args_list:
            self.assertEqual(len(args[0]), 1)  # 1 arg
            self.assertEqual(args[1], {})  # no kwargs

            assert_msg(
                args[0][0],
                {
                    FTag.Symbol: "VOD.L",
                    FTag.Price: "123.45",
                    FTag.OrderQty: "9876",
                },
            )

    async def test_handle_read_partial_decode_logic_msg_buff_management(self):
        full = self.codec.encode(self.msg, self.session).encode()
        partial_1 = full[:20]
        partial_2 = full[20:]
        self.assertEqual((partial_1 + partial_2), full)

        msg_valid = b"8=FIX.4.4\x019=82\x0135=D\x0149=sender\x0156=target\x0134=1\x0152=20230919-07:13:26.808\x0144=123.45\x0138=9876\x0155=VOD.L\x0110=100\x01"  # noqa

        h = FIXConnectionHandler(
            self.engine, self.protocol, self.socket_reader_mock, None
        )
        with (patch.object(h, "process_message") as mock_process_message,):
            self.socket_reader_mock.read.side_effect = [
                b"abcd",
                msg_valid,
                asyncio.CancelledError,  # This stops infinite loop
            ]
            await asyncio.wait_for(h.handle_read(), 1)

        self.assertEqual(mock_process_message.call_count, 1)

    async def test_handle_read_partial_msg_oneafter_another(self):
        full = self.codec.encode(self.msg, self.session).encode()
        partial_1 = full[:20]
        partial_2 = full[20:]
        self.assertEqual((partial_1 + partial_2), full)

        self.socket_reader_mock.read.side_effect = [
            partial_1,
            # remainder comes with next valid message
            partial_2 + self.codec.encode(self.msg, self.session).encode(),
            asyncio.CancelledError,  # This stops infinite loop
        ]

        h = FIXConnectionHandler(
            self.engine, self.protocol, self.socket_reader_mock, None
        )

        with patch.object(h, "process_message") as mock_process_message:
            await asyncio.wait_for(h.handle_read(), 1)

        self.assertEqual(mock_process_message.call_count, 2)

        for args in mock_process_message.call_args_list:
            self.assertEqual(len(args[0]), 1)  # 1 arg
            self.assertEqual(args[1], {})  # no kwargs

            assert_msg(
                args[0][0],
                {
                    FTag.Symbol: "VOD.L",
                    FTag.Price: "123.45",
                    FTag.OrderQty: "9876",
                },
            )
