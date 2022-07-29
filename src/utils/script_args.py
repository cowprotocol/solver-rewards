"""Common method for initializing setup for scripts"""
import argparse
from dataclasses import dataclass

from duneapi.api import DuneAPI
from src.models import AccountingPeriod


@dataclass
class ScriptArgs:
    """A collection of common script arguments relevant to this project"""

    dune: DuneAPI
    period: AccountingPeriod
    post_tx: bool
    dry_run: bool


def generic_script_init(description: str) -> ScriptArgs:
    """
    1. parses parses command line arguments,
    2. establishes dune connection
    and returns this info
    """
    parser = argparse.ArgumentParser(description)
    parser.add_argument(
        "--start", type=str, help="Accounting Period Start", required=True
    )
    parser.add_argument(
        "--post-tx",
        type=bool,
        help="Flag indicating whether multisend should be posted to safe "
        "(requires valid env var `PROPOSER_PK`)",
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
        dune=DuneAPI.new_from_environment(),
        period=AccountingPeriod(args.start),
        post_tx=args.post_tx,
        dry_run=args.dry_run,
    )
