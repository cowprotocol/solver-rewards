"""
Common location for shared resources throughout the project.
"""
from __future__ import annotations

import urllib.parse
from datetime import datetime, timedelta

from dune_client.types import QueryParameter

DATE_FORMAT = "%Y-%m-%d-%H:%M:%S"


class AccountingPeriod:
    """Class handling the date arithmetic and string conversions for date intervals"""

    def __init__(self, start: str, end: str = None, length_days: int = 7):
        self.start = datetime.strptime(start, DATE_FORMAT)
        if end:
            self.end = datetime.strptime(end, DATE_FORMAT)
        else:
            self.end = self.start + timedelta(days=length_days)

    def __str__(self) -> str:
        return "-to-".join(
            [self.start.strftime(DATE_FORMAT), self.end.strftime(DATE_FORMAT)]
        )

    def __hash__(self) -> int:
        """Turns (1985-03-10, 1994-04-05) into only the digits 1985031019940405"""
        return int(
            "".join([self.start.strftime("%Y%m%d"), self.end.strftime("%Y%m%d")])
        )

    def as_query_params(self) -> list[QueryParameter]:
        """Returns commonly used (StartTime, EndTime) query parameters"""
        return [
            QueryParameter.date_type("StartTime", self.start),
            QueryParameter.date_type("EndTime", self.end),
        ]

    def dashboard_url(self) -> str:
        """Constructs Solver Accounting Dashboard URL for Period"""
        base = "https://dune.com/cowprotocol/"
        slug = "cow-solver-rewards"
        query = f"?StartTime={self.start}&EndTime={self.end}"
        return base + urllib.parse.quote_plus(slug + query, safe="=&?")

    def unusual_slippage_url(self) -> str:
        """Returns a link to unusual slippage query for period"""
        base = "https://dune.com/queries/1688044"
        query = f"?StartTime={self.start}&EndTime={self.end}"
        return base + urllib.parse.quote_plus(query, safe="=&?")
