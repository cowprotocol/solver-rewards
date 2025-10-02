"""
Localized account of all Queries related to this project's main functionality
"""

from __future__ import annotations

from copy import copy
from dataclasses import dataclass

from dune_client.query import QueryBase
from dune_client.types import QueryParameter


@dataclass
class QueryData:
    """Stores name and a version of the query for each query."""

    name: str
    query: QueryBase

    def __init__(self, name: str, q_id: int) -> None:
        self.name = name
        self.query = QueryBase(q_id, name)

    def with_params(self, params: list[QueryParameter]) -> QueryBase:
        """Copies the query, adds parameters, returning the copy."""
        query_copy = copy(self.query)
        query_copy.params = params
        return query_copy


QUERIES = {
    "PERIOD_BLOCK_INTERVAL": QueryData(
        name="Block Interval for Accounting Period",
        q_id=3333356,
    ),
    "DASHBOARD_SLIPPAGE": QueryData(
        name="Period Solver Rewards",
        q_id=2510345,
    ),
}
