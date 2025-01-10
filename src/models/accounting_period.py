"""
Common location for shared resources throughout the project.
"""

from __future__ import annotations

from datetime import datetime, timedelta

from dune_client.types import QueryParameter

DATE_FORMAT = "%Y-%m-%d"


class AccountingPeriod:
    """Class handling the date arithmetic and string conversions for date intervals"""

    def __init__(self, start: str, length_days: int = 7):
        self.start = datetime.strptime(start, DATE_FORMAT)
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
        """Returns commonly used (start_time, end_time) query parameters"""
        return [
            QueryParameter.date_type("start_time", self.start),
            QueryParameter.date_type("end_time", self.end),
        ]
