"""
Script to generate the CSV Airdrop file for Solver Rewards over an Accounting Period
"""
from __future__ import annotations

from dataclasses import dataclass
from typing import Optional

import pandas as pd

from dune_client.types import Address
from eth_typing.encoding import HexStr
from gnosis.safe.multi_send import MultiSendOperation, MultiSendTx
from web3 import Web3

from src.abis.load import erc20
from src.models.token import TokenType, Token

ERC20_CONTRACT = erc20()


@dataclass
class CSVTransfer:
    """Essentially a Transfer Object, but with amount as float instead of amount_wei"""

    token_type: TokenType
    # Safe airdrop uses null address for native asset transfers
    token_address: Optional[Address]
    receiver: Address
    # safe-airdrop uses float amounts!
    amount: float

    @classmethod
    def from_transfer(cls, transfer: Transfer) -> CSVTransfer:
        """Converts WeiTransfer into CSVTransfer"""
        return cls(
            token_type=transfer.token_type,
            token_address=transfer.token.address if transfer.token else None,
            receiver=transfer.recipient,
            # The primary purpose for this class is to convert amount_wei to amount
            amount=transfer.amount,
        )


@dataclass
class Transfer:
    """Total amount reimbursed for accounting period"""

    token: Optional[Token]
    _recipient: Address
    amount_wei: int

    def __init__(self, token: Optional[Token], recipient: Address, amount_wei: int):
        assert amount_wei > 0, f"Can't construct negative transfer of {amount_wei}"

        self.token = token
        self._recipient = recipient
        self.amount_wei = amount_wei

        # It ensures that transfers are grouped
        # 1. first by initial recipient (i.e. solvers),
        # 2. then by token address (with native ETH last) and
        # 3. finally ordered by amount descending (so that largest in category occur first).
        self._sort_key = (recipient, str(token), -amount_wei)

    @classmethod
    def from_dict(cls, obj: dict[str, str]) -> Transfer:
        """Converts Dune data dict to object with types"""
        token_address = obj.get("token_address", None)
        return cls(
            token=Token(token_address) if token_address else None,
            recipient=Address(obj["receiver"]),
            amount_wei=int(obj["amount"]),
        )

    @classmethod
    def from_dataframe(cls, pdf: pd.DataFrame) -> list[Transfer]:
        """Converts Pandas Dataframe into list of Transfers"""
        return [
            cls(
                token=Token(row["token_address"]) if row["token_address"] else None,
                recipient=Address(row["receiver"]),
                amount_wei=int(row["amount"]),
            )
            for _, row in pdf.iterrows()
        ]

    @staticmethod
    def summarize(transfers: list[Transfer]) -> str:
        """Summarizes transfers with totals"""
        eth_total = sum(
            t.amount_wei for t in transfers if t.token_type == TokenType.NATIVE
        )
        cow_total = sum(
            t.amount_wei for t in transfers if t.token_type == TokenType.ERC20
        )
        return (
            f"Total ETH Funds needed: {eth_total / 10 ** 18:.4f}\n"
            f"Total COW Funds needed: {cow_total / 10 ** 18:.4f}\n"
        )

    @property
    def recipient(self) -> Address:
        """Read access to the recipient of a transfer"""
        return self._recipient

    @property
    def sort_key(self) -> tuple[Address, str, int]:
        """Read access to the recipient of a transfer"""
        return self._sort_key

    @staticmethod
    def consolidate(transfer_list: list[Transfer]) -> list[Transfer]:
        """
        Removes redundancy of a transfer list by consolidating _duplicate transfers_.
        Duplicates defined as transferring the same token to one recipient multiple times.
        This optimizes gas cost of multiple transfers.
        """

        transfer_dict: dict[tuple, Transfer] = {}
        for transfer in transfer_list:
            key = (transfer.recipient, transfer.token)
            if key in transfer_dict:
                transfer_dict[key] = transfer_dict[key].merge(transfer)
            else:
                transfer_dict[key] = transfer
        return sorted(
            transfer_dict.values(),
            key=lambda t: (-t.amount, t.recipient, t.token),
        )

    @property
    def token_type(self) -> TokenType:
        """Returns the type of transfer (Native or ERC20)"""
        if self.token is None:
            return TokenType.NATIVE
        return TokenType.ERC20

    @property
    def amount(self) -> float:
        """Returns transfer amount_wei in units"""
        if self.token_type == TokenType.NATIVE:
            return self.amount_wei / int(10**18)
        # This case was handled above.
        assert self.token is not None
        return self.amount_wei / int(10**self.token.decimals)

    def merge(self, other: Transfer) -> Transfer:
        """
        Merge two transfers (acts like addition) if all fields except amount are equal,
        returns a transfer who amount is the sum.
        Merges incur information loss (particularly in the category of redirects).
        Note that two transfers of the same token with different receivers,
        but redirected to the same address, will get merged and original receivers will be forgotten
        """
        merge_requirements = [
            self.recipient == other.recipient,
            self.token == other.token,
        ]
        if all(merge_requirements):
            return Transfer(
                token=self.token,
                recipient=self.recipient,
                amount_wei=self.amount_wei + other.amount_wei,
            )
        raise ValueError(
            f"Can't merge transfers {self}, {other}. "
            f"Requirements met {merge_requirements}"
        )

    def as_multisend_tx(self) -> MultiSendTx:
        """Converts Transfer into encoded MultiSendTx bytes"""
        receiver = Web3.to_checksum_address(self.recipient.address)
        if self.token_type == TokenType.NATIVE:
            return MultiSendTx(
                operation=MultiSendOperation.CALL,
                to=receiver,
                value=self.amount_wei,
                data=HexStr("0x"),
            )
        if self.token_type == TokenType.ERC20:
            assert self.token is not None
            return MultiSendTx(
                operation=MultiSendOperation.CALL,
                to=str(self.token.address),
                value=0,
                data=ERC20_CONTRACT.encodeABI(
                    fn_name="transfer", args=[receiver, self.amount_wei]
                ),
            )
        raise ValueError(f"Unsupported type {self.token_type}")

    def __str__(self) -> str:
        if self.token_type == TokenType.NATIVE:
            return f"TransferETH(receiver={self.recipient}, amount={self.amount})"
        if self.token_type == TokenType.ERC20:
            return (
                f"Transfer("
                f"token={self.token}, "
                f"recipient={self.recipient}, "
                f"amount={self.amount})"
            )
        raise ValueError(f"Invalid Token Type {self.token_type}")

    @staticmethod
    def sort_list(transfer_list: list[Transfer]) -> None:
        """
        This is the preferred and tested sort order we use for generating the transfer file.
        Note that this method mutates the input data and nothing in returned.
        """
        transfer_list.sort(key=lambda t: t.sort_key)
