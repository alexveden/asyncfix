from math import isnan, nan
from unittest.mock import AsyncMock, MagicMock

from asyncfix import FIXMessage, FMsg, FTag
from asyncfix.connection import AsyncFIXConnection, ConnectionState
from asyncfix.journaler import Journaler
from asyncfix.protocol import FIXProtocol44, FIXSchema
from asyncfix.protocol.common import FExecType, FOrdStatus
from asyncfix.protocol.order_single import FIXNewOrderSingle


class FIXTester:
    def __init__(
        self,
        schema: FIXSchema | None = None,
        connection: AsyncFIXConnection | None = None,
    ):
        self.registered_orders = {}
        self.schema = schema
        self.order_id = 0
        self.exec_id = 10000
        self.conn_init = connection
        self.conn_accept = None
        self.initiator_sent: list[FIXMessage] = []
        """list of fix messages sent by self.connection.send_msg()"""

        self.acceptor_rcv_que: list[tuple(FIXMessage, bytes)] = []

        self.acceptor_sent: list[FIXMessage] = []
        """list of fix messages sent by FIXTester.reply()"""

        if connection:
            assert isinstance(connection, AsyncFIXConnection)
            # target and session swapped! Because we mimic the server
            j = Journaler()
            self.conn_accept = AsyncFIXConnection(
                FIXProtocol44(),
                target_comp_id=self.conn_init._session.sender_comp_id,
                sender_comp_id=self.conn_init._session.target_comp_id,
                journaler=j,
                host="localhost",
                port="64444",
                heartbeat_period=30,
                logger=self.conn_init.log,
            )
            self.conn_accept._connection_state = (
                ConnectionState.NETWORK_CONN_ESTABLISHED
            )
            self.conn_accept._session.next_num_out = connection._session.next_num_in
            self.conn_accept._session.next_num_in = connection._session.next_num_out

            connection._socket_writer = MagicMock()
            connection._socket_writer.write.side_effect = (
                self._conn_socket_write_initiator
            )
            connection._socket_writer.drain = AsyncMock()
            connection._socket_writer.wait_closed = AsyncMock()

            self.conn_accept._socket_writer = MagicMock()
            self.conn_accept._socket_writer.write.side_effect = (
                self._conn_socket_write_acceptor
            )
            self.conn_accept._socket_writer.drain = AsyncMock()
            self.conn_accept._socket_writer.drain.side_effect = (
                self._conn_socket_drain_acceptor
            )
            self._socket_drain_in_coro = None
            self.conn_accept._socket_writer.wait_closed = AsyncMock()

    def set_next_num(self, num_in=None, num_out=None):
        if num_in is not None:
            assert isinstance(num_in, int)
            assert num_in > 0
            self.conn_accept._session.next_num_in = num_in
        if num_out is not None:
            assert isinstance(num_out, int)
            assert num_out > 0
            self.conn_accept._session.next_num_out = num_out

    def reset_messages(self):
        self.initiator_sent.clear()
        self.acceptor_rcv_que.clear()
        self.acceptor_sent.clear()

    def acceptor_sent_query(
        self,
        tags: tuple[FTag | str | int] | None = None,
        index: int = -1,
    ) -> dict[FTag | str, str]:
        """
        Query message sent from FIXTester to initiator
        Args:
            tags:
            index:

        Returns:


        """
        return self.acceptor_sent[index].query(*tags)

    def initiator_sent_query(
        self,
        tags: tuple[FTag | str | int] | None = None,
        index: int = -1,
    ) -> dict[FTag | str, str]:
        """
        Query message sent from initiator to FixTester

        Args:
            tags:
            index:

        Returns:


        """
        return self.initiator_sent[index].query(*tags)

    def _conn_socket_write_initiator(self, data):
        msg, _, _ = self.conn_init._codec.decode(data, silent=False)
        if self.schema:
            self.schema.validate(msg)
        self.initiator_sent.append(msg)
        self.acceptor_rcv_que.append((msg, data))

    def _conn_socket_write_acceptor(self, data):
        msg, _, _ = self.conn_accept._codec.decode(data, silent=False)
        if self.schema:
            self.schema.validate(msg)
        self.acceptor_sent.append(msg)

        self._socket_drain_in_coro = self.conn_init._process_message(msg, data)

    async def _conn_socket_drain_acceptor(self):
        try:
            if self._socket_drain_in_coro:
                await self._socket_drain_in_coro
        finally:
            self._socket_drain_in_coro = None

    async def process_msg_acceptor(self, index=None):
        """
        Processes all messages qued by initiator.send_msg() or single if `index` given

        Args:
            index: None - processes all messages in que, number - only one at that index

        """
        assert self.acceptor_rcv_que, "No messages in self.acceptor_rcv_que"

        while self.acceptor_rcv_que:
            (msg, raw) = self.acceptor_rcv_que.pop(0 if index is None else index)
            await self.conn_accept._process_message(msg, raw)
            if index is not None:
                break

    async def reply(self, msg: FIXMessage):
        if self.schema:
            self.schema.validate(msg)

        raw_msg = self.conn_accept._codec.encode(
            msg,
            self.conn_accept._session,
            raw_seq_num=FTag.MsgSeqNum in msg,
        ).encode()

        # Pretend the message was transfered to initiator
        decoded_msg, _, _ = self.conn_init._codec.decode(raw_msg, silent=False)

        if self.schema:
            self.schema.validate(decoded_msg)

        self.acceptor_sent.append(decoded_msg)

        await self.conn_init._process_message(decoded_msg, raw_msg)

        return decoded_msg

    def next_order_id(self) -> int:
        self.order_id += 1
        return self.order_id

    def next_exec_id(self) -> int:
        self.exec_id += 1
        return self.exec_id

    def order_register_single(self, o: FIXNewOrderSingle):
        self.registered_orders[o.clord_id] = o
        return True

    def fix_cxl_request(self, o: FIXNewOrderSingle) -> FIXMessage:
        assert o.can_cancel()  # new assert 2023-09-23
        m = o.cancel_req()
        if self.schema:
            self.schema.validate(m)
        self.registered_orders[o.clord_id] = o
        return m

    def fix_rep_request(
        self, o: FIXNewOrderSingle, price: float = nan, qty: float = nan
    ) -> FIXMessage:
        assert o.can_replace()
        m = o.replace_req(price, qty)
        if self.schema:
            self.schema.validate(m)
        self.registered_orders[o.clord_id] = o
        return m

    def fix_cxlrep_reject_msg(
        self,
        cxl_req: FIXMessage,
        ord_status: FOrdStatus,
    ) -> FIXMessage:
        clord_id = cxl_req[FTag.ClOrdID]
        orig_clord_id = cxl_req[FTag.OrigClOrdID]

        m = FIXMessage(FMsg.ORDERCANCELREJECT)
        m[37] = 0
        m[11] = clord_id
        m[41] = orig_clord_id
        m[39] = ord_status

        assert cxl_req.msg_type in [
            FMsg.ORDERCANCELREQUEST,
            FMsg.ORDERCANCELREPLACEREQUEST,
        ]

        if cxl_req.msg_type == FMsg.ORDERCANCELREQUEST:
            m[FTag.CxlRejResponseTo] = "1"
        elif cxl_req.msg_type == FMsg.ORDERCANCELREPLACEREQUEST:
            m[FTag.CxlRejResponseTo] = "2"

        if self.schema:
            self.schema.validate(m)

        return m

    def fix_exec_report_msg(
        self,
        order: FIXNewOrderSingle,
        clord_id: str,
        exec_type: FExecType,
        ord_status: FOrdStatus,
        cum_qty: float = nan,
        leaves_qty: float = nan,
        last_qty: float = nan,
        price: float = nan,
        order_qty: float = nan,
        orig_clord_id: str = None,
        avg_price: float = 0.0,
    ) -> FIXMessage:
        assert order.clord_id in self.registered_orders, "Unregistered order!"

        m = FIXMessage(FMsg.EXECUTIONREPORT)
        assert clord_id
        m[FTag.ClOrdID] = clord_id

        if order.order_id is None:
            order_id = self.next_order_id()
        else:
            order_id = order.order_id

        m[FTag.OrderID] = order_id
        m[FTag.ExecID] = self.next_exec_id()

        if orig_clord_id:
            m[FTag.OrigClOrdID] = orig_clord_id
        m[FTag.ExecType] = exec_type
        m[FTag.OrdStatus] = ord_status
        m[FTag.Side] = order.side

        if isnan(order_qty):
            order_qty = order.qty
        else:
            assert (
                exec_type == FExecType.REPLACED
            ), "Only applicable to exec_type=5 (replace)"
            assert order_qty > 0

        if isnan(cum_qty):
            cum_qty = order.cum_qty
        else:
            assert cum_qty <= order.qty
            assert cum_qty >= 0
        m[FTag.CumQty] = cum_qty

        if isnan(leaves_qty):
            leaves_qty = order.leaves_qty
        else:
            assert leaves_qty >= 0
            assert leaves_qty <= order_qty

        m[FTag.LeavesQty] = leaves_qty
        assert (
            cum_qty + leaves_qty <= order_qty
        ), f"cum_qty[{cum_qty}] + leaves_qty[{leaves_qty}] <= order_qty[{order_qty}]"

        if not isnan(last_qty):
            assert not isnan(leaves_qty), "Must also set leaves_qty, when trade"
            assert not isnan(cum_qty), "Must also set cum_qty, when trade"
            assert (
                exec_type == FExecType.TRADE
            ), "Only applicable to exec_type=F (trade)"
            assert last_qty > 0
            m[FTag.LastQty] = last_qty
            assert (
                round(last_qty - (cum_qty - order.cum_qty), 3) == 0
            ), "Probably incorrect Trade qty"
        else:
            assert (
                exec_type != FExecType.TRADE
            ), "You must set last_qty when exec_type=F (trade)"

        if not isnan(price):
            assert (
                exec_type == FExecType.REPLACED
            ), "Only applicable to exec_type=5 (replace)"
        else:
            price = order.price

        order.set_instrument(m)

        order.set_price_qty(m, price, order_qty)
        m[FTag.AvgPx] = avg_price

        order.set_account(m)

        if (
            exec_type == FExecType.PENDING_CANCEL
            and ord_status == FOrdStatus.PENDING_CANCEL
        ):
            assert order.orig_clord_id
            assert order.clord_id
            assert order.clord_id != order.orig_clord_id
            assert order.cum_qty == cum_qty
            assert order.leaves_qty == leaves_qty

        if (
            ord_status == FOrdStatus.FILLED
            or ord_status == FOrdStatus.CANCELED
            or ord_status == FOrdStatus.REJECTED
            or ord_status == FOrdStatus.EXPIRED
        ):
            assert leaves_qty == 0, "New order report is finished, but LeavesQty != 0"

        if self.schema:
            self.schema.validate(m)
        return m

    def msg_logon(self, tags: dict | None = None):
        msg = FIXMessage(FMsg.LOGON, tags)
        if FTag.EncryptMethod not in msg:
            msg.set(FTag.EncryptMethod, 0)
        if FTag.HeartBtInt not in msg:
            msg.set(FTag.HeartBtInt, 30)

        if self.schema:
            self.schema.validate(msg)

        return msg

    def msg_logout(self) -> FIXMessage:
        msg = FIXMessage(FMsg.LOGOUT)

        if self.schema:
            self.schema.validate(msg)

        return msg

    def msg_heartbeat(self, test_req_id=None) -> FIXMessage:
        msg = FIXMessage(FMsg.HEARTBEAT)
        if test_req_id is not None:
            msg[FTag.TestReqID] = test_req_id

        if self.schema:
            self.schema.validate(msg)

        return msg

    def msg_test_request(self, test_req_id) -> FIXMessage:
        msg = FIXMessage(FMsg.TESTREQUEST)
        msg[FTag.TestReqID] = test_req_id

        if self.schema:
            self.schema.validate(msg)

        return msg

    def msg_sequence_reset(
        self, msg_seq_num: int, new_seq_no: int, is_gap_fill: bool = False
    ) -> FIXMessage:
        msg = FIXMessage(FMsg.SEQUENCERESET)
        msg.set(FTag.MsgSeqNum, msg_seq_num)
        msg.set(FTag.GapFillFlag, "Y" if is_gap_fill else "N")
        msg.set(FTag.NewSeqNo, new_seq_no)
        if self.schema:
            self.schema.validate(msg)
        return msg

    def msg_resend_request(self, begin_seq_no, end_seq_no="0") -> FIXMessage:
        msg = FIXMessage(FMsg.RESENDREQUEST)
        msg.set(FTag.BeginSeqNo, str(begin_seq_no))
        msg.set(FTag.EndSeqNo, str(end_seq_no))
        if self.schema:
            self.schema.validate(msg)
        return msg
