"""
Script to query and display total funds distributed for specified accounting period.
"""
from dataclasses import dataclass
from datetime import datetime

from duneapi.api import DuneAPI
from duneapi.types import DuneQuery, Network, QueryParameter, Address
from duneapi.util import open_query

from src.utils.dataset import index_by
from src.utils.script_args import generic_script_init

# pylint: disable=line-too-long
RECOGNIZED_BONDING_POOLS = [
    "('\\x8353713b6D2F728Ed763a04B886B16aAD2b16eBD'::bytea, 'Gnosis', '\\x6c642cafcbd9d8383250bb25f67ae409147f78b2'::bytea)",
    "('\\x5d4020b9261F01B6f8a45db929704b0Ad6F5e9E6'::bytea, 'CoW Services', '\\x423cec87f19f0778f549846e0801ee267a917935'::bytea)",
]


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
    pool_values = ",\n           ".join(RECOGNIZED_BONDING_POOLS)
    query = DuneQuery.from_environment(
        raw_sql="\n".join(
            [open_query("./queries/vouch_registry.sql"), "select * from valid_vouches"]
        ),
        network=Network.MAINNET,
        name="Solver Reward Targets",
        parameters=[
            QueryParameter.date_type("EndTime", end_time),
            QueryParameter.text_type("BondingPoolData", pool_values),
        ],
    )
    return parse_vouches(dune.fetch(query))


if __name__ == "__main__":
    dune_connection, accounting_period = generic_script_init(
        description="Fetch Reward Targets"
    )
    vouch_map = get_vouches(dune=dune_connection, end_time=accounting_period.end)

    for solver, vouch in vouch_map.items():
        print("Solver", solver, "Reward Target", vouch.reward_target)
