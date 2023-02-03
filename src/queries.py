"""
Localized account of all Queries related to this project's main functionality
"""
from __future__ import annotations

from copy import copy
from dataclasses import dataclass
from enum import Enum

from dune_client.query import Query
from dune_client.types import QueryParameter


class DuneVersion(Enum):
    """Dune Version Identifier"""

    V1 = "1"
    V2 = "2"

    @staticmethod
    def from_string(version_str: str) -> DuneVersion:
        """Constructor of Dune version from string"""
        try:
            return DuneVersion[version_str]
        except KeyError as err:
            raise ValueError(f"Invalid DuneVersion string {version_str}") from err


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

    def with_params(
        self, params: list[QueryParameter], dune_version: DuneVersion = DuneVersion.V2
    ) -> Query:
        """
        Copies the query and adds parameters to it, returning the copy.
        """
        # We currently default to the V1 Queries, soon to switch them out.
        query_copy = copy(self.v1_query)
        if dune_version == DuneVersion.V2:
            query_copy = copy(self.v2_query)

        query_copy.params = params
        return query_copy


QUERIES = {
    "TRADE_COUNT": QueryData(
        name="Trade Counts",
        v1_id=1393627,
        v2_id=1785586,
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
        v1_id=1870864,
        v2_id=1788438,
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
        filepath="period_totals.sql",
        v1_id=1687752,
        v2_id=1687870,
    ),
    "PERIOD_SLIPPAGE": QueryData(
        name="Solver Slippage for Period",
        filepath="period_slippage.sql",
        v1_id=1728478,
        v2_id=1956003,
    ),
}
