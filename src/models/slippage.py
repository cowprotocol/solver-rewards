"""
Dataclass for SolverSlippage along with Split Slippage class that handles a collection
of SolverSlippage objects.
"""

from __future__ import annotations

from dataclasses import dataclass

from dune_client.types import Address


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


@dataclass
class SplitSlippages:
    """Basic class to store the output of slippage fetching"""

    solvers_with_negative_total: list[SolverSlippage]
    solvers_with_positive_total: list[SolverSlippage]

    def __init__(self) -> None:
        self.solvers_with_negative_total = []
        self.solvers_with_positive_total = []

    @classmethod
    def from_data_set(cls, data_set: list[dict[str, str]]) -> SplitSlippages:
        """Constructs an object based on provided dataset"""
        results = cls()
        for row in data_set:
            results.append(slippage=SolverSlippage.from_dict(row))
        return results

    def append(self, slippage: SolverSlippage) -> None:
        """Appends the Slippage to the appropriate half based on signature of amount"""
        if slippage.amount_wei < 0:
            self.solvers_with_negative_total.append(slippage)
        else:
            self.solvers_with_positive_total.append(slippage)

    def __len__(self) -> int:
        return len(self.solvers_with_negative_total) + len(
            self.solvers_with_positive_total
        )

    def sum_negative(self) -> int:
        """Returns total negative slippage"""
        return sum(neg.amount_wei for neg in self.solvers_with_negative_total)

    def sum_positive(self) -> int:
        """Returns total positive slippage"""
        return sum(pos.amount_wei for pos in self.solvers_with_positive_total)
