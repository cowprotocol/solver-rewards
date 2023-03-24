"""Common method for initializing setup for scripts"""
import argparse
import os
from datetime import date, timedelta
from dataclasses import dataclass

from dune_client.client import DuneClient

from src.fetch.dune import DuneFetcher
from src.models.accounting_period import AccountingPeriod
from src.queries import DuneVersion


@dataclass
class ScriptArgs:
    """A collection of common script arguments relevant to this project"""

    dune: DuneFetcher
    post_tx: bool
    dry_run: bool
    pre_cip20: bool
    consolidate_transfers: bool
    min_transfer_amount_wei: int


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
        type=bool,
        help="Flag indicating whether multisend should be posted to safe "
        "(requires valid env var `PROPOSER_PK`)",
        default=False,
    )
    parser.add_argument(
        "--pre-cip20",
        type=bool,
        help="Flag payout should be made according to pre or post CIP-20. "
        "Default is set to the current reward scheme",
        default=False,
    )
    parser.add_argument(
        "--dune-version",
        type=DuneVersion,
        help="Which Dune Client version to use (legacy or official)",
        default=DuneVersion.V2,
        choices=list(DuneVersion),
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
        help="Ignore transfers with amount less than this",
        default=1000000000000000,
    )
    args = parser.parse_args()
    return ScriptArgs(
        dune=DuneFetcher(
            dune=DuneClient(os.environ["DUNE_API_KEY"]),
            period=AccountingPeriod(args.start),
            dune_version=args.dune_version,
        ),
        pre_cip20=args.pre_cip20,
        post_tx=args.post_tx,
        dry_run=args.dry_run,
        consolidate_transfers=args.consolidate_transfers,
        min_transfer_amount_wei=args.min_transfer_amount_wei,
    )
