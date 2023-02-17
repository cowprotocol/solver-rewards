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

from src.abis.load import erc20
from src.models.slippage import SolverSlippage
from src.models.token import TokenType, Token
from src.models.vouch import Vouch
from src.utils.print_store import Category, PrintStore


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
            receiver=transfer.receiver,
            # The primary purpose for this class is to convert amount_wei to amount
            amount=transfer.amount,
        )


@dataclass
class Transfer:
    """Total amount reimbursed for accounting period"""

    token: Optional[Token]
    receiver: Address
    amount_wei: int
    # This defaults to receiver if not otherwise specified.
    redirect_to: Optional[Address] = None

    @classmethod
    def from_dict(cls, obj: dict[str, str]) -> Transfer:
        """Converts Dune data dict to object with types"""
        token_address = obj.get("token_address", None)
        return cls(
            token=Token(token_address) if token_address else None,
            receiver=Address(obj["receiver"]),
            amount_wei=int(obj["amount"]),
        )

    @classmethod
    def from_dataframe(cls, pdf: pd.DataFrame) -> list[Transfer]:
        """Converts Pandas Dataframe into list of Transfers"""
        return [
            cls(
                token=Token(row["token_address"]) if row["token_address"] else None,
                receiver=Address(row["receiver"]),
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
        """The correct way to access the true recipient of a transfer"""
        return self.redirect_to if self.redirect_to is not None else self.receiver

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

    def add_slippage(self, slippage: SolverSlippage, log_saver: PrintStore) -> None:
        """Adds Adjusts Transfer amount by Slippage amount"""
        assert self.receiver == slippage.solver_address, "receiver != solver"
        adjustment = slippage.amount_wei
        log_saver.print(
            f"Deducting slippage for solver {self.receiver}"
            f"by {adjustment / 10 ** 18:.5f} ({slippage.solver_name})",
            category=Category.SLIPPAGE,
        )
        new_amount = self.amount_wei + adjustment
        if new_amount <= 0:
            raise ValueError(f"Invalid adjustment {self} by {adjustment / 10 ** 18}")
        self.amount_wei = new_amount

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
                receiver=self.recipient,
                amount_wei=self.amount_wei + other.amount_wei,
            )
        raise ValueError(
            f"Can't merge transfers {self}, {other}. "
            f"Requirements met {merge_requirements}"
        )

    def as_multisend_tx(self) -> MultiSendTx:
        """Converts Transfer into encoded MultiSendTx bytes"""
        receiver = self.recipient.address
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
                data=erc20().encodeABI(
                    fn_name="transfer", args=[receiver, self.amount_wei]
                ),
            )
        raise ValueError(f"Unsupported type {self.token_type}")

    def __str__(self) -> str:
        if self.token_type == TokenType.NATIVE:
            return f"TransferETH(receiver={self.recipient}, amount_wei={self.amount})"
        if self.token_type == TokenType.ERC20:
            return (
                f"Transfer("
                f"token_address={self.token}, "
                f"recipient={self.recipient}, "
                f"amount_wei={self.amount})"
            )
        raise ValueError(f"Invalid Token Type {self.token_type}")

    def try_redirect(
        self, redirects: dict[Address, Vouch], log_saver: PrintStore
    ) -> None:
        """
        Redirects Transfers via Address => Vouch.reward_target
        This function modifies self!
        """
        recipient = self.recipient
        if recipient in redirects:
            # Redirect COW rewards to reward target specific by VouchRegistry
            redirect_address = redirects[recipient].reward_target
            log_saver.print(
                f"Redirecting {recipient} Transfer of {self.amount} to {redirect_address}",
                category=Category.ETH_REDIRECT
                if self.token is None
                else Category.COW_REDIRECT,
            )
            self.redirect_to = redirect_address

    @classmethod
    def from_slippage(cls, slippage: SolverSlippage) -> Transfer:
        """
        Slippage is always in ETH, so this converts
        Slippage into an ETH Transfer with Null token address
        """
        return cls(
            token=None,
            receiver=slippage.solver_address,
            amount_wei=slippage.amount_wei,
        )

    @classmethod
    def sort_list(cls, transfer_list: list[Transfer]) -> None:
        """
        This is the preferred and tested sort order we use for generating the transfer file.
        It ensures that transfers are grouped
        1. first by initial recipient (i.e. solvers),
        2. then by token address (with native ETH last)
        and finally order by amount descending (so that largest in category occur first).
        Note that this method mutates the input data and nothing in returned.
        """
        transfer_list.sort(key=lambda t: (t.receiver, str(t.token), -t.amount))

    def __eq__(self, other: object) -> bool:
        if isinstance(other, Transfer):
            return all(
                [
                    self.recipient == other.recipient,
                    self.token == other.token,
                    self.amount_wei == other.amount_wei,
                ]
            )
        return False
