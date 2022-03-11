"""
Common location for shared resources throughout the project.
"""
import re
from enum import Enum
from typing import Optional
from dataclasses import dataclass

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
    from_token_address: Address
    to_token_address: Optional[Address]
    from_amount: int
    to_amount: Optional[int]

    # pylint: disable=too-many-arguments
    def __init__(self, transfer_type, from_token_address, to_token_address, from_amount, to_amount):
        self.transfer_type = transfer_type
        self.from_token_address = Address(from_token_address)
        self.to_token_address = Address(
            to_token_address) if to_token_address else None
        self.from_amount = int(from_amount)
        self.to_amount = int(to_amount) if to_amount else None


@dataclass
class SlippagePerSolver:
    """Slippage per solver"""
    eth_slippage_wei: int
    solver: Address

    def __init__(self, eth_slippage_wei, solver):
        self.eth_slippage_wei = eth_slippage_wei
        self.solver = Address(solver)
