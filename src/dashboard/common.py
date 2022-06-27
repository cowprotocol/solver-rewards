"""Common method for initializing setup for scripts"""
import argparse

from duneapi.api import DuneAPI


def arg_parse(description: str) -> tuple[DuneAPI, argparse.Namespace]:
    """
    1. Parses command line arguments
    2. Establishes dune connection and
    returns this info
    """
    parser = argparse.ArgumentParser(description)
    parser.add_argument(
        "--dashboard-slug",
        type=str,
        required=True,
        help="The hyphenated last part of the dashboard URL",
    )
    return DuneAPI.new_from_environment(), parser.parse_args()
