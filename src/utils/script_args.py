"""Common method for initializing setup for scripts"""
import argparse

from src.dune_analytics import DuneAnalytics
from src.models import AccountingPeriod


def generic_script_init(description: str) -> tuple[DuneAnalytics, AccountingPeriod]:
    """
    1. parses parses command line arguments,
    2. establishes dune connection
    and returns this info
    """
    parser = argparse.ArgumentParser(description)
    parser.add_argument(
        "--start", type=str, help="Accounting Period Start", required=True
    )
    args = parser.parse_args()

    return DuneAnalytics.new_from_environment(), AccountingPeriod(args.start)
