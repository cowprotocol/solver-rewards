"""
Dataclass for SolverSlippage along with Split Slippage class that handles a collection
of SolverSlippage objects.
"""

from __future__ import annotations

from dataclasses import dataclass
from enum import Enum
from typing import Hashable, Any

from dune_client.types import Address

from src.utils.query_file import (
    open_dashboard_query,
    open_query,
)


@dataclass
class SolverSlippage:
    """Total amount reimbursed for accounting period"""

    solver_address: Address
    solver_name: str
    # ETH amount (in WEI) to be deducted from Solver reimbursement
    amount_wei: int

    @classmethod
    def from_dict(cls, obj: dict[Hashable, Any]) -> SolverSlippage:
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
    def from_data_set(cls, data_set: list[dict[Hashable, Any]]) -> SplitSlippages:
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


class QueryType(Enum):
    """
    Determines type of slippage data to be fetched.
    The slippage subquery allows us to select from either of the two result tables defined here.
    """

    PER_TX = "results_per_tx"
    TOTAL = "results"
    UNUSUAL = "outliers"

    def __str__(self) -> str:
        return str(self.value)

    def select_statement(self) -> str:
        """Returns select statement to be used in slippage query."""
        if self in (QueryType.PER_TX, QueryType.TOTAL):
            return f"select * from {self}"
        if self == QueryType.UNUSUAL:
            return open_dashboard_query("unusual-slippage.sql")
        # Can only happen if types are added to the enum and not accounted for.
        raise ValueError(f"Invalid Query Type! {self}")


def slippage_query(query_type: QueryType = QueryType.TOTAL) -> str:
    """
    Constructs our slippage query by joining sub-queries
    Default query type input it total, but we can request
    per transaction results for testing
    """
    return "\n".join(
        [
            open_query("dune_v1/period_slippage.sql"),
            query_type.select_statement(),
        ]
    )
