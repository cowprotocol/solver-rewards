"""
Common location for shared resources throughout the project.
"""
from __future__ import annotations

from enum import Enum
from typing import Optional

from dune_client.types import Address

from src.constants import COW_TOKEN_ADDRESS, web3
from src.utils.token_details import get_token_decimals


class TokenType(Enum):
    """Classifications of CSV Airdrop Transfer Types"""

    NATIVE = "native"
    ERC20 = "erc20"

    # Technically the app also supports NFT transfers, but this is irrelevant here
    # NFT = 'nft'

    @classmethod
    def from_str(cls, type_str: str) -> TokenType:
        """Constructs Enum variant from string (case-insensitive)"""
        try:
            return cls[type_str.upper()]
        except KeyError as err:
            raise ValueError(f"No TokenType {type_str}!") from err

    def __str__(self) -> str:
        return str(self.value)


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
            decimals if decimals is not None else get_token_decimals(web3, address)
        )

    def __repr__(self) -> str:
        return str(self.address)

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
