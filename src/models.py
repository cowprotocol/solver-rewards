"""
Common location for shared resources throughout the project.
"""
from __future__ import annotations

import re
from dataclasses import dataclass
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


class TransferType(Enum):
    """
    Classifications of Internal Token Transfers
    """

    IN_AMM = "IN_AMM"
    OUT_AMM = "OUT_AMM"
    IN_USER = "IN_USER"
    OUT_USER = "OUT_USER"
    INTERNAL_TRADE = "INTERNAL_TRADE"

    @classmethod
    def from_str(cls, type_str: str) -> TransferType:
        """Constructs Enum variant from string (case-insensitive)"""
        try:
            return cls[type_str.upper()]
        except KeyError as err:
            raise ValueError(f"No TransferType {type_str}!") from err


@dataclass
class InternalTokenTransfer:
    """Total amount reimbursed for accounting period"""

    transfer_type: TransferType
    token: Address
    amount: int

    @classmethod
    def from_dict(cls, obj: dict[str, str]) -> InternalTokenTransfer:
        """Converts Dune data dict to object with types"""
        return cls(
            transfer_type=TransferType.from_str(obj["transfer_type"]),
            token=Address(obj["token"]),
            amount=int(obj["amount"]),
        )

    @staticmethod
    def filter_by(
        recs: list[InternalTokenTransfer], transfer_type: TransferType
    ) -> list[InternalTokenTransfer]:
        """Filters list of records returning only those with indicated TransferType"""
        return list(filter(lambda r: r.transfer_type == transfer_type, recs))

    @classmethod
    def internal_trades(
        cls, recs: list[InternalTokenTransfer]
    ) -> list[InternalTokenTransfer]:
        """Filters records returning only Internal Trade types."""
        return cls.filter_by(recs, TransferType.INTERNAL_TRADE)
