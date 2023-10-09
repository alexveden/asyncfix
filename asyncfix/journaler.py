import sqlite3

from asyncfix.errors import DuplicateSeqNoError, FIXMessageError
from asyncfix.message import MessageDirection
from asyncfix.session import FIXSession


class Journaler(object):
    def __init__(self, filename=None):
        if filename is None:
            self.conn = sqlite3.connect(":memory:")
        else:
            self.conn = sqlite3.connect(filename)

        self.cursor = self.conn.cursor()
        self.cursor.execute(
            "CREATE TABLE IF NOT EXISTS message("
            "seqNo INTEGER NOT NULL,"
            "session INTEGER NOT NULL,"
            "direction INTEGER NOT NULL,"
            "msg TEXT,"
            "PRIMARY KEY (seqNo, session, direction))"
        )

        self.cursor.execute(
            "CREATE TABLE IF NOT EXISTS session("
            "sessionId INTEGER PRIMARY KEY AUTOINCREMENT,"
            "targetCompId TEXT NOT NULL,"
            "senderCompId TEXT NOT NULL,"
            "outboundSeqNo INTEGER DEFAULT 0,"
            "inboundSeqNo INTEGER DEFAULT 0,"
            "UNIQUE (targetCompId, senderCompId))"
        )

    def sessions(self) -> dict[tuple[str, str], FIXSession]:
        sessions = {}
        self.cursor.execute(
            "SELECT sessionId, targetCompId, senderCompId, outboundSeqNo, inboundSeqNo"
            " FROM session"
        )
        for sessionInfo in self.cursor:
            session = FIXSession(sessionInfo[0], sessionInfo[1], sessionInfo[2])
            session.next_num_out = sessionInfo[3]
            session.next_num_in = sessionInfo[4] + 1
            sessions[(session.target_comp_id, session.sender_comp_id)] = session

        return sessions

    def create_or_load(self, target_comp_id, sender_comp_id) -> FIXSession:
        try:
            self.cursor.execute(
                "INSERT INTO session(targetCompId, senderCompId) VALUES(?, ?)",
                (target_comp_id, sender_comp_id),
            )
            session_id = self.cursor.lastrowid
            self.conn.commit()
            session = FIXSession(session_id, target_comp_id, sender_comp_id)
            session.next_num_out = 1
            session.next_num_in = 1
        except sqlite3.IntegrityError:
            self.cursor.execute(
                "SELECT sessionId, targetCompId, senderCompId, outboundSeqNo, inboundSeqNo"  # noqa
                " FROM session WHERE targetCompId = ? AND senderCompId = ?",
                (target_comp_id, sender_comp_id),
            )
            session_data = next(self.cursor)
            session = FIXSession(session_data[0], session_data[1], session_data[2])
            session.next_num_out = session_data[3] + 1
            session.next_num_in = session_data[4] + 1
            # print(f"Journaler: Loaded session: {session}")
        return session

    @staticmethod
    def find_seq_no(msg: bytes) -> int:
        try:
            i_start = msg.index(b"\x0134=")
            i_end = msg.index(b"\x01", i_start + 1)
            return int(msg[i_start + 4 : i_end])
        except Exception:
            raise FIXMessageError(f"tag 34 is not found or invalid, in message: {msg}")

    def set_seq_num(
        self,
        session: FIXSession,
        next_num_out: int | None = None,
        next_num_in: int | None = None,
    ):
        if next_num_out is not None:
            assert next_num_out > 0
            session.next_num_out = next_num_out
        else:
            next_num_out = session.next_num_out

        if next_num_in is not None:
            assert next_num_in > 0
            session.next_num_in = next_num_in
        else:
            next_num_in = session.next_num_in

        self.cursor.execute(
            "UPDATE session SET inboundSeqNo=?, outboundSeqNo=?  WHERE sessionId = ?",
            (next_num_in - 1, next_num_out - 1, session.key),
        )

        self.cursor.execute(
            "DELETE FROM message WHERE session = ? AND seqNo >= ? AND direction = ?",
            (session.key, next_num_in, MessageDirection.INBOUND.value),
        )
        self.cursor.execute(
            "DELETE FROM message WHERE session = ? AND seqNo >= ? AND direction = ?",
            (session.key, next_num_out, MessageDirection.OUTBOUND.value),
        )

    def persist_msg(self, msg: bytes, session: FIXSession, direction: MessageDirection):
        assert isinstance(msg, bytes), "expected encoded message"
        seq_no = self.find_seq_no(msg)
        try:
            self.cursor.execute(
                "INSERT INTO message VALUES(?, ?, ?, ?)",
                (seq_no, session.key, direction.value, msg),
            )
            if direction == MessageDirection.OUTBOUND:
                self.cursor.execute(
                    "UPDATE session SET outboundSeqNo=? WHERE sessionId = ?",
                    (seq_no, session.key),
                )
            elif direction == MessageDirection.INBOUND:
                self.cursor.execute(
                    "UPDATE session SET inboundSeqNo=? WHERE sessionId = ?",
                    (seq_no, session.key),
                )

            self.conn.commit()
        except sqlite3.IntegrityError as e:
            raise DuplicateSeqNoError("%s is a duplicate, error %s" % (seq_no, repr(e)))

    def recover_msg(
        self, session: FIXSession, direction: MessageDirection, seq_no: int
    ) -> bytes:
        msgs = self.recover_messages(session, direction, seq_no, seq_no)
        if msgs:
            return msgs[0]
        else:
            return None

    def recover_messages(
        self, session: FIXSession, direction: MessageDirection, start_seq_no, end_seq_no
    ) -> list[bytes]:
        self.cursor.execute(
            "SELECT msg FROM message WHERE session = ? AND direction = ? AND seqNo >= ?"
            " AND seqNo <= ? ORDER BY seqNo",
            (session.key, direction.value, start_seq_no, end_seq_no),
        )
        msgs = []
        for msg in self.cursor:
            assert isinstance(msg[0], bytes)
            msgs.append(msg[0])
        return msgs

    def get_all_msgs(
        self,
        sessions: list[FIXSession] | None = None,
        direction: MessageDirection | None = None,
    ):
        sql = "SELECT seqNo, msg, direction, session FROM message"
        clauses = []
        args = []
        if sessions is not None and len(sessions) != 0:
            skeys = []
            for s in sessions:
                key = s.key if isinstance(s, FIXSession) else s
                skeys.append(key)

            clauses.append("session in (" + ",".join("?" * len(sessions)) + ")")
            args.extend(skeys)

        if direction is not None:
            clauses.append("direction = ?")
            args.append(direction.value)

        if clauses:
            sql = sql + " WHERE " + " AND ".join(clauses)

        sql = sql + " ORDER BY rowid"

        self.cursor.execute(sql, tuple(args))
        msgs = []
        for msg in self.cursor:
            msgs.append((msg[0], msg[1], msg[2], msg[3]))

        return msgs
