"""
Localized account of all Queries related to this project's main functionality
"""
from __future__ import annotations

from copy import copy
from dataclasses import dataclass

from dune_client.query import Query
from dune_client.types import QueryParameter


@dataclass
class QueryData:
    """Stores name and a version of the query for each query."""

    name: str
    query: Query

    def __init__(self, name: str, q_id: int, filepath: str) -> None:
        self.name = name
        self.filepath = filepath
        self.query = Query(q_id, name)

    def with_params(self, params: list[QueryParameter]) -> Query:
        """Copies the query, adds parameters, returning the copy."""
        query_copy = copy(self.query)
        query_copy.params = params
        return query_copy


QUERIES = {
    "TRADE_COUNT": QueryData(
        name="Trade Counts",
        q_id=1785586,
        filepath="dune_trade_counts.sql",
    ),
    "PERIOD_BLOCK_INTERVAL": QueryData(
        name="Block Interval for Accounting Period",
        filepath="period_block_interval.sql",
        q_id=1541504,
    ),
    "RISK_FREE_BATCHES": QueryData(
        name="Risk Free Batches",
        filepath="risk_free_batches.sql",
        q_id=1788438,
    ),
    "VOUCH_REGISTRY": QueryData(
        name="Vouch Registry",
        filepath="vouch_registry.sql",
        q_id=1541516,
    ),
    "ETH_SPENT": QueryData(
        name="ETH Reimbursement",
        filepath="eth_spent.sql",
        q_id=1320174,
    ),
    "PERIOD_SLIPPAGE": QueryData(
        name="Solver Slippage for Period",
        filepath="period_slippage.sql",
        q_id=2259597,
    ),
    "DASHBOARD_SLIPPAGE": QueryData(
        name="Dashboard Slippage for Period",
        filepath="not currently stored in project",
        q_id=2283297,
    ),
}
