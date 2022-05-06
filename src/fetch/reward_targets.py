"""
Script to query and display total funds distributed for specified accounting period.
"""
from dataclasses import dataclass
from typing import Optional

from duneapi.api import DuneAPI
from duneapi.types import DuneQuery, Network, QueryParameter
from duneapi.util import open_query

from src.models import Address
from src.utils.dataset import index_by

RECOGNIZED_BONDING_POOLS = [
    "('\\x8353713b6D2F728Ed763a04B886B16aAD2b16eBD'::bytea, 'Gnosis', '\\x6c642cafcbd9d8383250bb25f67ae409147f78b2'::bytea)",
    "('\\x5d4020b9261F01B6f8a45db929704b0Ad6F5e9E6'::bytea, 'CoW Services', '\\x423cec87f19f0778f549846e0801ee267a917935'::bytea)",
]
REAL_VOUCH_EVENTS = """
    select evt_block_number, evt_index, solver, "cowRewardTarget", "bondingPool", sender
    from cow_protocol."VouchRegister_evt_Vouch"
    """.strip()
REAL_INVALIDATION_EVENTS = """
    select evt_block_number, evt_index, solver, "bondingPool", sender
    from cow_protocol."VouchRegister_evt_InvalidateVouch"
    """.strip()


@dataclass
class Vouch:
    """Data triplet linking solvers to bonding pools and COW reward destination"""

    solver: Address
    reward_target: Address
    bonding_pool: Address


def vouch_query(
    vouch_events: str = REAL_VOUCH_EVENTS,
    invalidation_events: str = REAL_INVALIDATION_EVENTS,
    bonding_pools: Optional[list[str]] = None,
) -> str:
    if bonding_pools is None:
        bonding_pools = RECOGNIZED_BONDING_POOLS
    query_template = open_query("./queries/vouch_registry.sql")
    pool_values = ",\n           ".join(bonding_pools)
    query = (
        query_template.replace("{{BondingPoolData}}", pool_values)
        .replace("{{VouchEvents}}", vouch_events)
        .replace("{{InvalidationEvents}}", invalidation_events)
    )
    return query


def get_vouches(dune: DuneAPI, query: str = vouch_query()) -> dict[Address, Vouch]:
    """
    Fetches & Returns Dune Results for accounting period totals.
    """
    query = DuneQuery.from_environment(
        raw_sql=query,
        network=Network.MAINNET,
        name="Solver Reward Targets",
        parameters=[QueryParameter.text_type("Scenario", "real")],
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
