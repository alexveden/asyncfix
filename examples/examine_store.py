"""FIX Journaler DB CLI."""
import argparse
import logging
import os
import sys

from asyncfix.journaler import Journaler
from asyncfix.message import MessageDirection


def main():
    """Entry point."""
    logging.basicConfig(format="%(asctime)s %(message)s", level=logging.INFO)

    parser = argparse.ArgumentParser(
        description="Examine the contents of the store file."
    )
    group = parser.add_mutually_exclusive_group()
    group.add_argument(
        "-l", "--list", dest="list", action="store_true", help="list available streams"
    )
    group.add_argument(
        "-s",
        "--sessions",
        dest="sessions",
        nargs="+",
        action="store",
        metavar=("s1", "s2"),
        help="session to examine",
    )
    parser.add_argument("filename", action="store", help="filename of the store file")
    parser.add_argument(
        "-d",
        "--direction",
        dest="direction",
        choices=["in", "out", "both"],
        action="store",
        default="both",
        help="filename of the store file",
    )

    args = parser.parse_args()

    if not os.path.exists(args.filename):
        print(f"filename not exists {args.filename}")
        sys.exit(1)

    journal = Journaler(args.filename)

    if args.list is True:
        # list all sessions
        row_format = "{:^15}|" * 3
        separator_format = "{:->15}|" * 3
        for session in journal.sessions():
            print(row_format.format("Session Id", "TargetCompId", "SenderCompId"))
            print(separator_format.format("", "", ""))
            print(
                row_format.format(
                    session.key, session.target_comp_id, session.sender_comp_id
                )
            )
        print(separator_format.format("", "", ""))
    else:
        # list all messages in that stream
        direction = (
            None
            if args.direction == "both"
            else (
                MessageDirection.INBOUND
                if args.direction == "in"
                else MessageDirection.OUTBOUND
            )
        )
        for seqNo, msg, msgDirection, session in journal.get_all_msgs(
            args.sessions, direction
        ):
            mfmt = msg.decode()
            mfmt = mfmt.replace("\x01", "|")
            d = "---->" if msgDirection == MessageDirection.OUTBOUND.value else "<----"
            print("{:>3} {:^5} [{:>5}] {}".format(session, d, seqNo, mfmt))


if __name__ == "__main__":
    main()
