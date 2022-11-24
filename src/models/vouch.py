"""
Script to query and display total funds distributed for specified accounting period.
"""
from dataclasses import dataclass

from dune_client.types import Address

from src.utils.dataset import index_by

RECOGNIZED_BONDING_POOLS = [
    "('0x8353713b6D2F728Ed763a04B886B16aAD2b16eBD', 'Gnosis', "
    "'0x6c642cafcbd9d8383250bb25f67ae409147f78b2')",
    "('0x5d4020b9261F01B6f8a45db929704b0Ad6F5e9E6', 'CoW Services', "
    "'0x423cec87f19f0778f549846e0801ee267a917935')",
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
