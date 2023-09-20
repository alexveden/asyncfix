from asyncfix.journaler import Journaler
from asyncfix.message import FIXMessage
from asyncfix.session import FIXSession


class FIXEngine(object):
    def __init__(self, journalfile=None):
        self.journaller = Journaler(journalfile)
        self.sessions: dict[str, FIXSession] = {}

        # We load all sessions from the journal and add to our list
        for session in self.journaller.sessions():
            self.sessions[session.key] = session

    def validate_session(self, target_comp_id, sender_comp_id):
        # this make any session we receive valid
        return True

    def should_resend_message(self, session: FIXSession, msg: FIXMessage):
        # we should resend all application messages
        return True

    def create_session(self, target_comp_id, sender_comp_id):
        if self.find_session_by_comp_ids(target_comp_id, sender_comp_id) is None:
            session = self.journaller.create_session(target_comp_id, sender_comp_id)
            self.sessions[session.key] = session
        else:
            raise RuntimeError("Failed to add session with duplicate key")
        return session

    def get_session(self, identifier):
        try:
            return self.sessions[identifier]
        except KeyError:
            return None

    def find_session_by_comp_ids(self, target_comp_id, sender_comp_id):
        sessions = [
            x
            for x in self.sessions.values()
            if x.target_comp_id == target_comp_id and x.sender_comp_id == sender_comp_id
        ]
        if sessions is not None and len(sessions) != 0:
            return sessions[0]
        return None

    def get_or_create_session_from_comp_ids(self, target_comp_id, sender_comp_id):
        session = self.find_session_by_comp_ids(target_comp_id, sender_comp_id)
        if session is None:
            if self.validate_session(target_comp_id, sender_comp_id):
                session = self.create_session(target_comp_id, sender_comp_id)

        return session
