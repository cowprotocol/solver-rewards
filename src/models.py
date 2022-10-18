"""
Common location for shared resources throughout the project.
"""
from __future__ import annotations

from datetime import datetime, timedelta

# pylint: disable=too-few-public-methods
from typing import Optional

from duneapi.api import DuneAPI
from duneapi.types import Address, DuneQuery, Network, QueryParameter
from duneapi.util import open_query

from src.constants import COW_TOKEN_ADDRESS
from src.utils.token_details import get_token_decimals


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
                raw_sql=open_query("./queries/period_block_interval.sql"),
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


class Token:
    """
    Token class consists of token `address` and additional `decimals` value.
    The constructor exists in a way that we can either
    - provide the decimals (for unit testing) which avoids making web3 calls
    - fetch the token decimals with eth_call.
    Since we primarily work with the COW token, the decimals are hardcoded here.
    """

    def __init__(self, address: str | Address, decimals: Optional[int] = None):
        if isinstance(address, str):
            address = Address(address)
        self.address = address

        if address == COW_TOKEN_ADDRESS:
            # Avoid Web3 Calls for main branch of program.
            decimals = 18

        self.decimals = (
            decimals if decimals is not None else get_token_decimals(address)
        )

    def __eq__(self, other: object) -> bool:
        if isinstance(other, Token):
            return self.address == other.address and self.decimals == other.decimals
        return False

    def __lt__(self, other: object) -> bool:
        if isinstance(other, Token):
            return self.address < other.address
        return False

    def __hash__(self) -> int:
        return self.address.__hash__()
