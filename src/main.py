"""Main project entry point (used by docker container)"""
import argparse
import sys
from enum import Enum

from src.fetch.transfer_file import run as solver_payout
from src.update.reward_history import run as dune_sync


class RunCommand(Enum):
    """Enum for supported commands"""

    SOLVER_PAYOUT = "PAYOUT"
    DUNE_SYNC = "SYNC"


if __name__ == "__main__":
    parser = argparse.ArgumentParser()
    parser.add_argument(
        "-c",
        "--command",
        type=RunCommand,
        choices=list(RunCommand),
    )
    args, _ = parser.parse_known_args()

    if args.command == RunCommand.DUNE_SYNC:
        dune_sync()
        sys.exit()
    if args.command == RunCommand.SOLVER_PAYOUT:
        solver_payout()
        sys.exit()
    raise ValueError(f"Unknown Command {args.command}")
