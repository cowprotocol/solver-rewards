"""
Common location for shared resources throughout the project.
"""
from __future__ import annotations

import re
from dataclasses import dataclass
from enum import Enum
from typing import Optional

from web3 import Web3


class Network(Enum):
    """
    Enum for EVM network. Meant to be used everywhere instead of strings
    """
    MAINNET = 'mainnet'
    GCHAIN = 'gchain'


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

    def __str__(self):
        return str(self.address)

    def __eq__(self, other):
        if isinstance(other, Address):
            return self.address == other.address
        return False

    @staticmethod
    def _is_valid(address: str) -> bool:
        match_result = re.match(
            pattern=r'^(0x)?[0-9a-f]{40}$',
            string=address,
            flags=re.IGNORECASE
        )
        return match_result is not None


@dataclass
class InternalTokenTransfer:
    """Total amount reimbursed for accounting period"""
    transfer_type: str
    from_token: Address
    to_token: Optional[Address]
    from_amount: int
    to_amount: Optional[int]

    @classmethod
    def from_dict(cls, obj: dict) -> InternalTokenTransfer:
        return cls(
            transfer_type=obj['transfer_type'],
            from_token=Address(obj['token_from']),
            to_token=Address(obj['token_to']) if obj['token_to'] else None,
            from_amount=int(obj['amount_from']),
            to_amount=int(obj['amount_to']) if obj['amount_to'] else None,
        )


@dataclass
class SolverSlippage:
    """Slippage per solver"""
    eth_amount_wei: int
    solver: Address

    def __init__(self, eth_slippage_wei, solver):
        self.eth_amount_wei = eth_slippage_wei
        self.solver = Address(solver)
