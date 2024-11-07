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
    min_transfer_amount_wei: int
    min_transfer_amount_cow_atoms: int
    ignore_slippage: bool


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
        help="Flag indicating whether script should not post alerts or transactions. "
        "Only relevant in combination with --post-tx True"
        "Primarily intended for deployment in staging environment.",
    )
    parser.add_argument(
        "--min-transfer-amount-wei",
        type=int,
        help="Ignore ETH transfers with amount less than this",
        default=1000000000000000,
    )
    parser.add_argument(
        "--min-transfer-amount-cow-atoms",
        type=int,
        help="Ignore COW transfers with amount less than this",
        default=20000000000000000000,
    )
    parser.add_argument(
        "--ignore-slippage",
        action="store_true",
        help="Flag for ignoring slippage computations",
    )
    args = parser.parse_args()
    return ScriptArgs(
        start=args.start,
        post_tx=args.post_tx,
        dry_run=args.dry_run,
        min_transfer_amount_wei=args.min_transfer_amount_wei,
        min_transfer_amount_cow_atoms=args.min_transfer_amount_cow_atoms,
        ignore_slippage=args.ignore_slippage,
    )
