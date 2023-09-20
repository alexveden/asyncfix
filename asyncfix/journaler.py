import sqlite3
import pickle
from asyncfix.message import MessageDirection, FIXMessage
from asyncfix.session import FIXSession


class DuplicateSeqNoError(Exception):
    pass


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
            "session TEXT NOT NULL,"
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

    def sessions(self):
        sessions = []
        self.cursor.execute(
            "SELECT sessionId, targetCompId, senderCompId, outboundSeqNo, inboundSeqNo"
            " FROM session"
        )
        for sessionInfo in self.cursor:
            session = FIXSession(sessionInfo[0], sessionInfo[1], sessionInfo[2])
            session.snd_seq_num = sessionInfo[3]
            session.next_expected_msg_seq_num = sessionInfo[4] + 1
            sessions.append(session)

        return sessions

    def create_session(self, target_comp_id, sender_comp_id) -> FIXSession:
        session = None
        try:
            self.cursor.execute(
                "INSERT INTO session(targetCompId, senderCompId) VALUES(?, ?)",
                (target_comp_id, sender_comp_id),
            )
            sessionId = self.cursor.lastrowid
            self.conn.commit()
            session = FIXSession(sessionId, target_comp_id, sender_comp_id)
        except sqlite3.IntegrityError:
            raise RuntimeError(
                "Session already exists for TargetCompId: %s SenderCompId: %s"
                % (target_comp_id, sender_comp_id)
            )

        return session

    def persist_msg(
        self, msg: FIXMessage, session: FIXSession, direction: MessageDirection
    ):
        msgStr = pickle.dumps(msg)
        seqNo = msg["34"]
        try:
            self.cursor.execute(
                "INSERT INTO message VALUES(?, ?, ?, ?)",
                (seqNo, session.key, direction.value, msgStr),
            )
            if direction == MessageDirection.OUTBOUND:
                self.cursor.execute("UPDATE session SET outboundSeqNo=?", (seqNo,))
            elif direction == MessageDirection.INBOUND:
                self.cursor.execute("UPDATE session SET inboundSeqNo=?", (seqNo,))

            self.conn.commit()
        except sqlite3.IntegrityError as e:
            raise DuplicateSeqNoError("%s is a duplicate, error %s" % (seqNo, repr(e)))

    def recover_msg(self, session: FIXSession, direction: MessageDirection, seq_no):
        try:
            msgs = self.recover_msgs(session, direction, seq_no, seq_no)
            return msgs[0]
        except IndexError:
            return None

    def recover_msgs(
        self, session: FIXSession, direction: MessageDirection, start_seq_no, end_seq_no
    ):
        self.cursor.execute(
            "SELECT msg FROM message WHERE session = ? AND direction = ? AND seqNo >= ?"
            " AND seqNo <= ? ORDER BY seqNo",
            (session.key, direction.value, start_seq_no, end_seq_no),
        )
        msgs = []
        for msg in self.cursor:
            msgs.append(pickle.loads(msg[0]))
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
            clauses.append("session in (" + ",".join("?" * len(sessions)) + ")")
            args.extend(sessions)
        if direction is not None:
            clauses.append("direction = ?")
            args.append(direction.value)

        if clauses:
            sql = sql + " WHERE " + " AND ".join(clauses)

        sql = sql + " ORDER BY rowid"

        self.cursor.execute(sql, tuple(args))
        msgs = []
        for msg in self.cursor:
            msgs.append((msg[0], pickle.loads(msg[1]), msg[2], msg[3]))

        return msgs
