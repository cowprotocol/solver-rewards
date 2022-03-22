"""
Common location for shared resources throughout the project.
"""
from __future__ import annotations

import re
from datetime import datetime, timedelta
from enum import Enum

from web3 import Web3


class Network(Enum):
    """
    Enum for EVM network. Meant to be used everywhere instead of strings
    """

    MAINNET = "mainnet"
    GCHAIN = "gchain"


# pylint: disable=too-few-public-methods
class Address:
    """
    Class representing Ethereum Address as a hexadecimal string of length 42.
    The string must begin with '0x' and the other 40 characters
    are digits 0-9 or letters a-f. Upon creation (from string) addresses
    are validated and stored in their check-summed format.
    """

    def __init__(self, address: str):
        if Address._is_valid(address):
            self.address: str = Web3.toChecksumAddress(address)
        else:
            raise ValueError(f"Invalid Ethereum Address {address}")

    def __str__(self) -> str:
        return str(self.address)

    def __eq__(self, other: object) -> bool:
        if isinstance(other, Address):
            return self.address == other.address
        return False

    def __hash__(self) -> int:
        return self.address.__hash__()

    @classmethod
    def zero(cls) -> Address:
        """Returns Null Ethereum Address"""
        return cls("0x0000000000000000000000000000000000000000")

    @staticmethod
    def _is_valid(address: str) -> bool:
        match_result = re.match(
            pattern=r"^(0x)?[0-9a-f]{40}$", string=address, flags=re.IGNORECASE
        )
        return match_result is not None


class AccountingPeriod:
    """Class handling the date arithmetic and string conversions for date intervals"""

    def __init__(self, start: str, length_days: int = 7):
        self.start = datetime.strptime(start, "%Y-%m-%d").date()
        self.end = self.start + timedelta(days=length_days)

    def __str__(self) -> str:
        return "-to-".join(
            [self.start.strftime("%Y-%m-%d"), self.end.strftime("%Y-%m-%d")]
        )
