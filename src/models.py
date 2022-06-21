"""
Common location for shared resources throughout the project.
"""
from __future__ import annotations

from datetime import datetime, timedelta


# pylint: disable=too-few-public-methods
class AccountingPeriod:
    """Class handling the date arithmetic and string conversions for date intervals"""

    def __init__(self, start: str, length_days: int = 7):
        self.start = datetime.strptime(start, "%Y-%m-%d")
        self.end = self.start + timedelta(days=length_days)

    @classmethod
    def from_end_date(cls, end: datetime, length_days: int = 7):
        start_date = end - timedelta(days=length_days)
        start = start_date.strftime("%Y-%m-%d")
        return cls(start, length_days)

    @classmethod
    def from_end_str(cls, end: str, length_days: int = 7):
        return cls.from_end_date(datetime.strptime(end, "%Y-%m-%d"), length_days)

    def __str__(self) -> str:
        return "-to-".join(
            [self.start.strftime("%Y-%m-%d"), self.end.strftime("%Y-%m-%d")]
        )
