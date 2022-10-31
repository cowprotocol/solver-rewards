"""
Dataclass for SolverSlippage along with Split Slippage class that handles a collection
of SolverSlippage objects.
"""

from __future__ import annotations

from dataclasses import dataclass

from duneapi.types import Address


@dataclass
class SolverSlippage:
    """Total amount reimbursed for accounting period"""

    solver_address: Address
    solver_name: str
    # ETH amount (in WEI) to be deducted from Solver reimbursement
    amount_wei: int

    @classmethod
    def from_dict(cls, obj: dict[str, str]) -> SolverSlippage:
        """Converts Dune data dict to object with types"""
        return cls(
            solver_address=Address(obj["solver_address"]),
            solver_name=obj["solver_name"],
            amount_wei=int(obj["eth_slippage_wei"]),
        )
