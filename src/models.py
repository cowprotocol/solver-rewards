"""
Common location for shared resources throughout the project.
"""
from __future__ import annotations

from datetime import datetime, timedelta


# pylint: disable=too-few-public-methods
from typing import Optional

from duneapi.types import Address

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


class Token:
    """
    Token class consists of token address an additional decimals value.
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
