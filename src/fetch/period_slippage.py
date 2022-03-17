"""A standalone script for fetching Solver Slippage for Accounting Period"""
from __future__ import annotations

from dataclasses import dataclass
from pprint import pprint

from src.dune_analytics import DuneAnalytics, QueryParameter
from src.file_io import File
from src.models import AccountingPeriod, Address, Network
from src.token_list import ALLOWED_TOKEN_LIST_URL, get_trusted_tokens_from_url
from src.utils.script_args import generic_script_init


def allowed_token_list_query(token_list: list[str]) -> str:
    """Constructs sub query for allowed tokens"""
    values = ",".join(f"('\\{address[1:]}' :: bytea)" for address in token_list)
    query = f"allow_listed_tokens as (select * from (VALUES {values}) AS t (token)),"
    return query


def prepend_to_sub_query(query: str, table_to_add: str) -> str:
    """prepends query with table immediately after with statement"""
    if query[0:4].lower() != "with":
        raise ValueError(f"Type {query} does not start with 'with'!")
    return "\n".join([query[0:4], table_to_add, query[5:]])


def add_token_list_table_to_query(original_sub_query: str) -> str:
    """Inserts the token_list table right after the WITH statement into the sql query"""
    token_list = get_trusted_tokens_from_url(ALLOWED_TOKEN_LIST_URL)
    sql_query_for_allowed_token_list = allowed_token_list_query(token_list)
    return prepend_to_sub_query(original_sub_query, sql_query_for_allowed_token_list)


def slippage_query(dune: DuneAnalytics) -> str:
    """Constructs our slippage query by joining sub-queries"""
    path = "./queries/slippage"
    slippage_sub_query = dune.open_query(
        File("subquery_batchwise_internal_transfers.sql", path).filename()
    )
    select_slippage_query = dune.open_query(
        File("select_slippage_results.sql", path).filename()
    )
    return "\n".join(
        [add_token_list_table_to_query(slippage_sub_query), select_slippage_query]
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


@dataclass
class SplitSlippages:
    """Basic class to store the output of slippage fetching"""

    negative: list[SolverSlippage]
    positive: list[SolverSlippage]

    def __init__(self) -> None:
        self.negative = []
        self.positive = []

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


def get_period_slippage(
    dune: DuneAnalytics,
    period: AccountingPeriod,
) -> SplitSlippages:
    """
    Executes & Fetches results of slippage query per solver for specified accounting period.
    Returns a class representation of the results as two lists (positive & negative).
    """
    data_set = dune.fetch(
        query_str=slippage_query(dune),
        network=Network.MAINNET,
        name="Slippage Accounting",
        parameters=[
            QueryParameter.date_type("StartTime", period.start),
            QueryParameter.date_type("EndTime", period.end),
            QueryParameter.text_type("TxHash", "0x"),
            QueryParameter.text_type("ResultTable", "results"),
        ],
    )
    results = SplitSlippages()
    for row in data_set:
        results.append(slippage=SolverSlippage.from_dict(row))

    return results


if __name__ == "__main__":
    dune_connection, accounting_period = generic_script_init(
        description="Fetch Accounting Period Totals"
    )
    slippage_for_period = get_period_slippage(
        dune=dune_connection, period=accounting_period
    )
    pprint(slippage_for_period)
