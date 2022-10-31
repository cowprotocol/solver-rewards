"""
Common location for shared resources throughout the project.
"""
from __future__ import annotations

import urllib.parse
from datetime import datetime, timedelta

from duneapi.api import DuneAPI
from duneapi.types import DuneQuery, Network, QueryParameter
from duneapi.util import open_query

from src.utils.query_file import query_file


class AccountingPeriod:
    """Class handling the date arithmetic and string conversions for date intervals"""

    def __init__(self, start: str, length_days: int = 7):
        self.start = datetime.strptime(start, "%Y-%m-%d")
        self.end = self.start + timedelta(days=length_days)

    def __str__(self) -> str:
        return "-to-".join(
            [self.start.strftime("%Y-%m-%d"), self.end.strftime("%Y-%m-%d")]
        )

    def __hash__(self) -> int:
        """Turns (1985-03-10, 1994-04-05) into only the digits 1985031019940405"""
        return int(
            "".join([self.start.strftime("%Y%m%d"), self.end.strftime("%Y%m%d")])
        )

    def get_block_interval(self, dune: DuneAPI) -> tuple[str, str]:
        """Returns block numbers corresponding to date interval"""
        results = dune.fetch(
            query=DuneQuery.from_environment(
                raw_sql=open_query(query_file("period_block_interval.sql")),
                name=f"Block Interval for Accounting Period {self}",
                network=Network.MAINNET,
                parameters=[
                    QueryParameter.date_type("StartTime", self.start),
                    QueryParameter.date_type("EndTime", self.end),
                ],
            )
        )
        assert len(results) == 1, "Block Interval Query should return only 1 result!"
        return str(results[0]["start_block"]), str(results[0]["end_block"])

    def dashboard_url(self) -> str:
        """Constructs Solver Accounting Dashboard URL for Period"""
        base = "https://dune.com/gnosis.protocol/"
        slug = "solver-rewards-accounting-v2"
        query = f"?StartTime={self.start}&EndTime={self.end}&PeriodHash={hash(self)}"
        return base + urllib.parse.quote_plus(slug + query, safe="=&?")

    def unusual_slippage_url(self) -> str:
        """Returns a link to unusual slippage query for period"""
        base = "https://dune.com/queries/645559"
        query = f"?StartTime={self.start}&EndTime={self.end}"
        return base + urllib.parse.quote_plus(query, safe="=&?")
