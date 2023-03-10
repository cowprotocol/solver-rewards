"""Common method for initializing setup for scripts"""
import argparse
import os
from datetime import date, timedelta
from dataclasses import dataclass

from dune_client.client import DuneClient

from src.fetch.dune import DuneFetcher
from src.models.accounting_period import AccountingPeriod
from src.pg_client import MultiInstanceDBFetcher
from src.queries import DuneVersion


@dataclass
class ScriptArgs:
    """A collection of common script arguments relevant to this project"""

    dune: DuneFetcher
    orderbook: MultiInstanceDBFetcher
    post_tx: bool
    dry_run: bool
    post_cip20: bool
    consolidate_transfers: bool


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
        "--post-cip20",
        type=bool,
        help="Flag payout should be made according to pre or post CIP 20 "
        "(temporary during switch over)",
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
    args = parser.parse_args()
    return ScriptArgs(
        dune=DuneFetcher(
            dune=DuneClient(os.environ["DUNE_API_KEY"]),
            period=AccountingPeriod(args.start),
            dune_version=args.dune_version,
        ),
        orderbook=MultiInstanceDBFetcher(
            [os.environ["PROD_DB_URL"], os.environ["BARN_DB_URL"]]
        ),
        post_cip20=args.post_cip20,
        post_tx=args.post_tx,
        dry_run=args.dry_run,
        consolidate_transfers=args.consolidate_transfers,
    )
