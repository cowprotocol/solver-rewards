"""Common method for initializing setup for scripts"""
import argparse
import os
from datetime import date, timedelta
from dataclasses import dataclass

from dune_client.client import DuneClient
from duneapi.api import DuneAPI

from src.fetch.dune import DuneFetcher
from src.models.accounting_period import AccountingPeriod


def previous_tuesday(day: date = date.today()) -> date:
    """
    Returns the previous Tuesday for a given date (defaulting to today).
    If the day is a Tuesday, then the previous Tuesday is the one before
    """
    week_day = day.weekday()
    if week_day > 1:
        return day - timedelta(days=week_day - 1)
    return day - timedelta(days=6 + week_day)


@dataclass
class ScriptArgs:
    """A collection of common script arguments relevant to this project"""

    dune: DuneFetcher
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
        "--start",
        type=str,
        help="Accounting Period Start. Defaults to previous Tuesday",
        default=str(previous_tuesday(date.today())),
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
        dune=DuneFetcher(
            dune_v1=DuneAPI.new_from_environment(),
            dune=DuneClient(os.environ["DUNE_API_KEY"]),
            period=AccountingPeriod(args.start),
        ),
        post_tx=args.post_tx,
        dry_run=args.dry_run,
    )
