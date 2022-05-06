"""
Script to query and display total funds distributed for specified accounting period.
"""
from dataclasses import dataclass

from duneapi.api import DuneAPI
from duneapi.types import DuneQuery, Network
from duneapi.util import open_query

from src.models import Address
from src.utils.dataset import index_by


@dataclass
class Vouch:
    """Data triplet linking solvers to bonding pools and COW reward destination"""

    solver: Address
    reward_target: Address
    bonding_pool: Address


def get_vouches(dune: DuneAPI) -> dict[Address, Vouch]:
    """
    Fetches & Returns Dune Results for accounting period totals.
    """
    query = DuneQuery.from_environment(
        raw_sql=open_query("./queries/vouch_registry.sql"),
        network=Network.MAINNET,
        name="Solver Reward Targets",
    )
    data_set = dune.fetch(query)
    result_list = [
        Vouch(
            solver=Address(rec["solver"]),
            reward_target=Address(rec["reward_target"]),
            bonding_pool=Address(rec["pool"]),
        )
        for rec in data_set
    ]
    # Indexing here ensures the solver's returned from Dune are unique!
    return index_by(result_list, "solver")


if __name__ == "__main__":
    dune_conn = DuneAPI.new_from_environment()
    vouch_map = get_vouches(dune=dune_conn)

    for solver, vouch in vouch_map.items():
        print("Solver", solver, "Reward Target", vouch.reward_target)
