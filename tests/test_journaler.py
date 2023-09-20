import unittest

from asyncfix.connection import MessageDirection
from asyncfix.journaler import Journaler
from asyncfix.message import FIXContainer, FIXMessage
from asyncfix.session import FIXSession


class JournalerTests(unittest.TestCase):
    def msg_tag34(self, tag34):
        msg = FIXMessage("AB")
        msg.set("45", "dgd")
        msg.set("32", "aaaa")
        msg.set("323", "bbbb")

        rptgrp1 = FIXContainer()
        rptgrp1.set("611", "aaa")
        rptgrp1.set("612", "bbb")
        rptgrp1.set("613", "ccc")

        msg.add_group("444", rptgrp1, 0)
        msg.set("34", str(tag34))
        return msg

    def testAddExtractMsg(self):
        journal = Journaler()

        session = FIXSession(1, "S1", "T1")

        for i in range(0, 5):
            msg = self.msg_tag34(i)
            journal.persist_msg(msg, session, MessageDirection.OUTBOUND)

        msg = journal.recover_msg(session, MessageDirection.OUTBOUND, 1)

    def testAddExtractMultipleMsgs(self):
        journal = Journaler()

        session = FIXSession(1, "S1", "T1")

        for i in range(0, 5):
            msg = self.msg_tag34(i)
            journal.persist_msg(msg, session, MessageDirection.OUTBOUND)

        msgs = journal.recover_msgs(session, MessageDirection.OUTBOUND, 0, 4)
        for i in range(0, len(msgs)):
            msg = self.msg_tag34(i)
            self.assertEqual(msg, msgs[i])
