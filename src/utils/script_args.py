"""Common method for initializing setup for scripts"""

import argparse
from datetime import date, timedelta
from dataclasses import dataclass


@dataclass
class ScriptArgs:
    """A collection of common script arguments relevant to this project"""

    start: str
    post_tx: bool
    dry_run: bool
    send_to_slack: bool
    fetch_from_analytics_db: bool


def generic_script_init(description: str) -> ScriptArgs:
    """
    1. parses parses command line arguments,
    2. establishes dune connection
    and returns this info
    """
    parser = argparse.ArgumentParser(description)
    parser.add_argument(
        "--start",
        type=str,
        help="Accounting Period Start. Defaults to previous Tuesday",
        default=str(date.today() - timedelta(days=7)),
    )
    parser.add_argument(
        "--post-tx",
        action="store_true",
        help="Flag indicating whether multisend should be posted to safe "
        "(requires valid env var `PROPOSER_PK`)",
    )
    parser.add_argument(
        "--dry-run",
        action="store_true",
        help="Flag indicating whether script should not post alerts or transactions. ",
    )
    parser.add_argument(
        "--ignore-slippage",
        action="store_true",
        help="Flag for ignoring slippage computations",
    )
    parser.add_argument(
        "--send-to-slack",
        action="store_true",
        help="Flag indicating whether or not the script should send the results to a slack channel",
    )
    parser.add_argument(
        "--fetch-from-analytics-db",
        action="store_true",
        help="Flag indicating whether or not the script should fetch data from the analytics DB."
        "With this flag set, --ignore-slippage is ignored.",
    )
    args = parser.parse_args()
    return ScriptArgs(
        start=args.start,
        post_tx=args.post_tx,
        dry_run=args.dry_run,
        send_to_slack=args.send_to_slack,
        fetch_from_analytics_db=args.fetch_from_analytics_db,
    )
