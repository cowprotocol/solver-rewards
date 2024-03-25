"""Common method for initializing setup for scripts"""
import argparse
import os
from datetime import date, timedelta
from dataclasses import dataclass

from dune_client.client import DuneClient

from src.fetch.dune import DuneFetcher
from src.models.accounting_period import AccountingPeriod


@dataclass
class ScriptArgs:
    """A collection of common script arguments relevant to this project"""

    dune: DuneFetcher
    post_tx: bool
    dry_run: bool
    consolidate_transfers: bool
    min_transfer_amount_wei: int
    min_transfer_amount_cow_atoms: int


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
        "--end",
        type=str,
        help="Accounting Period Start. Defaults to today",
        default=str(date.today()),
    )
    parser.add_argument(
        "--post-tx",
        type=bool,
        help="Flag indicating whether multisend should be posted to safe "
        "(requires valid env var `PROPOSER_PK`)",
        default=False,
    )
    parser.add_argument(
        "--consolidate-transfers",
        type=bool,
        help="Flag to indicate whether payout transfer file should be optimized "
        "(i.e. squash transfers having same receiver-token pair) ",
        default=False,
    )
    parser.add_argument(
        "--dry-run",
        type=bool,
        help="Flag indicating whether script should not post alerts or transactions. "
        "Only relevant in combination with --post-tx True"
        "Primarily intended for deployment in staging environment.",
        default=False,
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
        default=100000000000000000000,
    )
    args = parser.parse_args()
    return ScriptArgs(
        dune=DuneFetcher(
            dune=DuneClient(os.environ["DUNE_API_KEY"]),
            period=AccountingPeriod(args.start, args.end),
        ),
        post_tx=args.post_tx,
        dry_run=args.dry_run,
        consolidate_transfers=args.consolidate_transfers,
        min_transfer_amount_wei=args.min_transfer_amount_wei,
        min_transfer_amount_cow_atoms=args.min_transfer_amount_cow_atoms,
    )
