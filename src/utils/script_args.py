"""Common method for initializing setup for scripts"""
import argparse

from src.dune_analytics import DuneAnalytics


def generic_script_init(description: str) -> tuple[DuneAnalytics, argparse.Namespace]:
    """
    1. parses parses command line arguments,
    2. establishes dune connection
    and returns this info
    """
    parser = argparse.ArgumentParser(description)
    parser.add_argument(
        "--start", type=str, help="Accounting Period Start", required=True
    )
    parser.add_argument("--end", type=str, help="Accounting Period End", required=True)

    return DuneAnalytics.new_from_environment(), parser.parse_args()
