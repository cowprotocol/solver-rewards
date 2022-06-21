"""
Script to query and display total funds distributed for specified accounting period.
"""
from dataclasses import dataclass
from datetime import datetime

from duneapi.api import DuneAPI
from duneapi.types import Address

from src.base_query import base_query
from src.models import AccountingPeriod
from src.utils.dataset import index_by
from src.utils.script_args import generic_script_init


@dataclass
class Vouch:
    """Data triplet linking solvers to bonding pools and COW reward destination"""

    solver: Address
    reward_target: Address
    bonding_pool: Address


def parse_vouches(raw_data: list[dict[str, str]]) -> dict[Address, Vouch]:
    """Parses the Dune Response of VouchRegistry query"""
    result_list = [
        Vouch(
            solver=Address(rec["solver"]),
            reward_target=Address(rec["reward_target"]),
            bonding_pool=Address(rec["pool"]),
        )
        for rec in raw_data
    ]
    # Indexing here ensures the solver's returned from Dune are unique!
    return index_by(result_list, "solver")


def get_vouches(dune: DuneAPI, end_time: datetime) -> dict[Address, Vouch]:
    """
    Fetches & Returns Parsed Results for VouchRegistry query.
    """
    query = base_query(
        name="Solver Reward Targets",
        select="select * from valid_vouches",
        period=AccountingPeriod.from_end_date(end_time),
    )
    return parse_vouches(dune.fetch(query))


if __name__ == "__main__":
    dune_connection, accounting_period = generic_script_init(
        description="Fetch Reward Targets"
    )
    vouch_map = get_vouches(dune=dune_connection, end_time=accounting_period.end)

    for solver, vouch in vouch_map.items():
        print("Solver", solver, "Reward Target", vouch.reward_target)
