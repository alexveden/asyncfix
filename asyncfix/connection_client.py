import asyncio
import sys
import time
from enum import Enum
import logging
from asyncfix import FTag, FMsg
from asyncfix.errors import FIXConnectionError
from asyncfix.codec import Codec
from asyncfix.message import FIXMessage, MessageDirection
from asyncfix.protocol import FIXProtocolBase
from asyncfix.session import FIXSession
from asyncfix.connection import ConnectionState, AsyncFIXConnection


class AsyncFIXClient(AsyncFIXConnection):
    def __init__(
        self,
        protocol: FIXProtocolBase,
        sender_comp_id: str,
        target_comp_id: str,
        host: str,
        port: int,
        heartbeat_period: int = 30,
        logger: logging.Logger | None = None,
    ):
        super().__init__(
            protocol=protocol,
            sender_comp_id=sender_comp_id,
            target_comp_id=target_comp_id,
            host=host,
            port=port,
            heartbeat_period=heartbeat_period,
            logger=logger,
        )

    async def connect(self):
        assert self.connection_state == ConnectionState.DISCONNECTED
        self.socket_reader, self.socket_writer = await asyncio.open_connection(
            self.host, self.port
        )
        self.connection_state = ConnectionState.CONNECTED
        await self.on_connect()

    async def _handle_resend_request(self, msg: FIXMessage):
        begin_seq_no = msg[FTag.BeginSeqNo]
        end_seq_no = msg[FTag.EndSeqNo]
        if int(end_seq_no) == 0:
            end_seq_no = sys.maxsize
        logging.info("Received resent request from %s to %s", begin_seq_no, end_seq_no)
        replay_msgs = self.engine.journaller.recover_msgs(
            self.session, MessageDirection.OUTBOUND, begin_seq_no, end_seq_no
        )
        gap_fill_begin = int(begin_seq_no)
        gap_fill_end = int(begin_seq_no)
        for replay_msg in replay_msgs:
            msg_seq_num = int(replay_msg[FTag.MsgSeqNum])
            if replay_msg[FTag.MsgType] in self.codec.protocol.session_message_types:
                gap_fill_end = msg_seq_num + 1
            else:
                if self.engine.should_resend_message(self.session, replay_msg):
                    if gap_fill_begin < gap_fill_end:
                        # we need to send a gap fill message
                        gap_fill_msg = FIXMessage(FMsg.SEQUENCERESET)
                        gap_fill_msg[FTag.GapFillFlag] = "Y"
                        gap_fill_msg[FTag.MsgSeqNum] = gap_fill_begin
                        gap_fill_msg[FTag.NewSeqNo] = str(gap_fill_end)
                        await self.send_msg(gap_fill_msg)

                    # and then resent the replayMsg
                    del replay_msg[FTag.BeginString]
                    del replay_msg[FTag.BodyLength]
                    del replay_msg[FTag.SendingTime]
                    del replay_msg[FTag.SenderCompID]
                    del replay_msg[FTag.TargetCompID]
                    del replay_msg[FTag.CheckSum]
                    replay_msg[FTag.PossDupFlag] = "Y"
                    await self.send_msg(replay_msg)

                    gap_fill_begin = msg_seq_num + 1
                else:
                    gap_fill_end = msg_seq_num + 1
                    await self.send_msg(replay_msg)

        if gap_fill_begin < gap_fill_end:
            # we need to send a gap fill message
            gap_fill_msg = FIXMessage(FMsg.SEQUENCERESET)
            gap_fill_msg[FTag.GapFillFlag] = "Y"
            gap_fill_msg[FTag.MsgSeqNum] = gap_fill_begin
            gap_fill_msg[FTag.NewSeqNo] = str(gap_fill_end)
            await self.send_msg(gap_fill_msg)

    async def on_session_message(self, msg: FIXMessage):
        responses = []

        recv_seq_no = msg[FTag.MsgSeqNum]

        msg_type = msg[FTag.MsgType]
        target_comp_d = msg[FTag.TargetCompID]
        sender_comp_id = msg[FTag.SenderCompID]

        if msg_type == FMsg.LOGON:
            if self.connection_state == ConnectionState.LOGGED_IN:
                self.log.warning(
                    "Client session already logged in - ignoring login request"
                )
            else:
                self.connection_state = ConnectionState.LOGGED_IN
                self.heartbeat_period = float(msg[FTag.HeartBtInt])
        elif self.connection_state == ConnectionState.LOGGED_IN:
            self.message_last_time = time.time()
            # compids are reversed here
            if not self.session.validate_comp_ids(sender_comp_id, target_comp_d):
                self.log.error("Received message with unexpected comp ids")
                await self.disconnect()
                return

            if msg_type == FMsg.LOGOUT:
                self.connection_state = ConnectionState.LOGGED_OUT
                await self.disconnect()
            elif msg_type == FMsg.TESTREQUEST:
                # https://www.fixtrading.org/standards/fix-session-layer-online/#message-exchange-during-a-fix-connection # noqa
                #    see "Test request processing" section
                #  required to reply with TestReqID from query
                hbt_msg = self.protocol.heartbeat()
                hbt_msg[FTag.TestReqID] = msg[FTag.TestReqID]
                await self.send_msg(hbt_msg)
            elif msg_type == FMsg.RESENDREQUEST:
                await self._handle_resend_request(msg)
            elif msg_type == FMsg.SEQUENCERESET:
                # we can treat GapFill and SequenceReset in the same way
                # in both cases we will just reset the seq number to the
                # NewSeqNo received in the message
                new_seq_no = msg[FTag.NewSeqNo]
                if msg[FTag.GapFillFlag] == "Y":
                    self.log.info(
                        "Received SequenceReset(GapFill) filling gap from %s to %s"
                        % (recv_seq_no, new_seq_no)
                    )
                self.session.set_recv_seq_no(int(new_seq_no) - 1)
                recv_seq_no = new_seq_no
        else:
            self.log.warning("Can't process message, counterparty is not logged in")

        return (recv_seq_no, responses)
