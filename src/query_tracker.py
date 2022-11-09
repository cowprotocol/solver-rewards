"""
Localized account of all Queries related to this project's main functionality
"""
from __future__ import annotations

from copy import copy
from dataclasses import dataclass

from dune_client.query import Query
from dune_client.types import QueryParameter

from src.utils.query_file import dashboard_file


@dataclass
class QueryData:
    """Stores name and a version of the query for each query."""

    name: str
    v1_query: Query
    v2_query: Query

    def __init__(self, name: str, v1_id: int, v2_id: int, filepath: str) -> None:
        self.name = name
        self.filepath = filepath
        self.v1_query = Query(v1_id, name)
        self.v2_query = Query(v2_id, name)

    def with_params(self, params: list[QueryParameter]) -> Query:
        """
        Copies the query and adds parameters to it, returning the copy.
        """
        # We currently default to the V1 Queries, soon to switch them out.
        query_copy = copy(self.v1_query)
        query_copy.params = params
        return query_copy


# raw_sql=open_query(query_file("dune_trade_counts.sql")),

QUERIES = {
    "TRADE_COUNT": QueryData(
        name="Trade Counts",
        v1_id=1393627,
        v2_id=1393633,
        filepath="dune_trade_counts.sql",
    ),
    "PERIOD_BLOCK_INTERVAL": QueryData(
        name="Block Interval for Accounting Period",
        filepath="period_block_interval.sql",
        v1_id=1328116,
        v2_id=1541504,
    ),
    "RISK_FREE_BATCHES": QueryData(
        name="Risk Free Batches",
        filepath="risk_free_batches.sql",
        v1_id=1432733,
        v2_id=1541507,
    ),
    "VOUCH_REGISTRY": QueryData(
        name="Vouch Registry",
        filepath="vouch_registry.sql",
        v1_id=674947,
        v2_id=1541516,
    ),
    "ETH_SPENT": QueryData(
        name="ETH Reimbursement",
        filepath="eth_spent.sql",
        v1_id=1320169,
        v2_id=1320174,
    ),
    "PERIOD_TOTALS": QueryData(
        name="Accounting Period Totals",
        filepath=dashboard_file("period-totals.sql"),
        v1_id=448457,
        v2_id=-1,  # Not implemented
    ),
}
