"""A standalone script for fetching Solver Slippage for Accounting Period"""
from __future__ import annotations

import logging.config
from dataclasses import dataclass
from enum import Enum
from pprint import pprint

from duneapi.api import DuneAPI
from duneapi.types import QueryParameter, DuneQuery, Network, Address, DuneRecord
from duneapi.util import open_query

from src.constants import MERGE_DATA
from src.models import AccountingPeriod
from src.token_list import fetch_trusted_tokens
from src.update.token_list import update_token_list
from src.utils.dataset import index_by
from src.utils.script_args import generic_script_init

log = logging.getLogger(__name__)
logging.config.fileConfig(fname="logging.conf", disable_existing_loggers=False)


SELECT_UNUSUAL_SLIPPAGE = """
select
    block_time,
    rpt.solver_name,
    concat('0x', encode(rpt.tx_hash, 'hex')) as tx_hash,
    usd_value,
    batch_value,
    100 * usd_value / batch_value as relative_slippage
from results_per_tx rpt
join gnosis_protocol_v2."batches" b
    on rpt.tx_hash = b.tx_hash
where abs(usd_value) > '{{SignificantValue}}'
and 100.0 * abs(usd_value) / batch_value > '{{RelativeTolerance}}'
order by relative_slippage"""


class QueryType(Enum):
    """
    Determines type of slippage data to be fetched.
    The slippage subquery allows us to select from either of the two result tables defined here.
    """

    PER_TX = "results_per_tx"
    TOTAL = "results"
    UNUSUAL = "outliers"

    def __str__(self) -> str:
        return self.value

    def select_statement(self) -> str:
        """Returns select statement to be used in slippage query."""
        if self in (QueryType.PER_TX, QueryType.TOTAL):
            return f"select * from {self}"
        if self == QueryType.UNUSUAL:
            return SELECT_UNUSUAL_SLIPPAGE
        # Can only happen if types are added to the enum and not accounted for.
        raise ValueError(f"Invalid Query Type! {self}")


def slippage_query(query_type: QueryType = QueryType.TOTAL) -> str:
    """
    Constructs our slippage query by joining sub-queries
    Default query type input it total, but we can request
    per transaction results for testing
    """
    return "\n".join(
        [open_query("./queries/period_slippage.sql"), query_type.select_statement()]
    )


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

    def merge(self, other: SolverSlippage, target: Address) -> SolverSlippage:
        """Merges two solver slippages as long as their names are the same."""
        assert (
            self.solver_name == other.solver_name
        ), "Can only merge solver with same name"
        return SolverSlippage(
            solver_name=self.solver_name,
            solver_address=target,
            amount_wei=self.amount_wei + other.amount_wei,
        )

    @classmethod
    def zero(cls, address: str | Address, name: str) -> SolverSlippage:
        """Used as default instance"""
        if isinstance(address, str):
            address = Address(address)
        return cls(solver_name=name, solver_address=address, amount_wei=0)


@dataclass
class SplitSlippages:
    """Basic class to store the output of slippage fetching"""

    negative: list[SolverSlippage]
    positive: list[SolverSlippage]

    def __init__(self) -> None:
        self.negative = []
        self.positive = []

    @classmethod
    def from_data_set(cls, data_set: list[dict[str, str]]) -> SplitSlippages:
        """Constructs an object based on provided dataset"""
        results = cls()
        all_slippages = [SolverSlippage.from_dict(row) for row in data_set]
        indexed_slippage = index_by(all_slippages, "solver_address")
        for name, (old, new) in MERGE_DATA.items():
            # Remove the old one.
            old_address, target = Address(old), Address(new)
            old_solver_slippage: SolverSlippage = indexed_slippage.pop(
                old_address, SolverSlippage.zero(address=old_address, name=name)
            )
            new_solver_slippage: SolverSlippage = indexed_slippage.pop(
                target, SolverSlippage.zero(address=target, name=name)
            )
            # Merge old with new.
            indexed_slippage[target] = new_solver_slippage.merge(
                old_solver_slippage, target
            )
        for slippage in indexed_slippage.values():
            results.append(slippage)
        return results

    def append(self, slippage: SolverSlippage) -> None:
        """Appends the Slippage to the appropriate half based on signature of amount"""
        if slippage.amount_wei < 0:
            self.negative.append(slippage)
        else:
            self.positive.append(slippage)

    def __len__(self) -> int:
        return len(self.negative) + len(self.positive)

    def sum_negative(self) -> int:
        """Returns total negative slippage"""
        return sum(neg.amount_wei for neg in self.negative)

    def sum_positive(self) -> int:
        """Returns total positive slippage"""
        return sum(pos.amount_wei for pos in self.positive)


def fetch_dune_slippage(
    dune: DuneAPI,
    period: AccountingPeriod,
) -> list[DuneRecord]:
    """Constructs query and fetches results for solver slippage"""
    query = DuneQuery.from_environment(
        raw_sql=slippage_query(),
        network=Network.MAINNET,
        name="Slippage Accounting",
        parameters=[
            QueryParameter.date_type("StartTime", period.start),
            QueryParameter.date_type("EndTime", period.end),
            QueryParameter.text_type("TxHash", "0x"),
        ],
    )
    return dune.fetch(query)


def get_period_slippage(
    dune: DuneAPI,
    period: AccountingPeriod,
) -> SplitSlippages:
    """
    Executes & Fetches results of slippage query per solver for specified accounting period.
    Returns a class representation of the results as two lists (positive & negative).
    """
    update_token_list(dune, fetch_trusted_tokens())
    data_set = fetch_dune_slippage(dune, period)
    return SplitSlippages.from_data_set(data_set)


if __name__ == "__main__":
    dune_connection, accounting_period = generic_script_init(
        description="Fetch Accounting Period Totals"
    )
    slippage_for_period = get_period_slippage(
        dune=dune_connection, period=accounting_period
    )
    pprint(slippage_for_period)
