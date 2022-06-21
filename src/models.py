"""
Common location for shared resources throughout the project.
"""
from __future__ import annotations

from datetime import datetime, timedelta


# pylint: disable=too-few-public-methods
class AccountingPeriod:
    """Class handling the date arithmetic and string conversions for date intervals"""

    def __init__(self, start: datetime | str, length_days: int = 7):
        if isinstance(start, str):
            start = datetime.strptime(start, "%Y-%m-%d")
        self.start = start
        self.end = start + timedelta(days=length_days)

    @classmethod
    def from_end(cls, end: datetime | str, length_days: int = 7) -> AccountingPeriod:
        """Constructs Accounting Period from end date"""
        if isinstance(end, str):
            end = datetime.strptime(end, "%Y-%m-%d")
        start = end - timedelta(days=length_days)
        return cls(start, length_days)

    def __str__(self) -> str:
        return "-to-".join(
            [self.start.strftime("%Y-%m-%d"), self.end.strftime("%Y-%m-%d")]
        )
