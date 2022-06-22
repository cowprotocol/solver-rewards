"""Script to generate the CSV Airdrop file for Solver Rewards over an Accounting Period"""
from __future__ import annotations

import urllib.parse
from dataclasses import dataclass
from enum import Enum
from typing import Optional

from duneapi.api import DuneAPI
from duneapi.file_io import File, write_to_csv
from duneapi.types import DuneQuery, QueryParameter, Network, Address
from duneapi.util import open_query

from src.fetch.period_slippage import (
    SolverSlippage,
    get_period_slippage,
    detect_unusual_slippage,
)
from src.fetch.reward_targets import get_vouches

from src.models import AccountingPeriod
from src.utils.dataset import index_by
from src.utils.script_args import generic_script_init

COW_TOKEN = Address("0xDEf1CA1fb7FBcDC777520aa7f396b4E015F497aB")
COW_PER_BATCH = 50
COW_PER_TRADE = 35


def safe_url() -> str:
    """URL to CSV Airdrop App in CoW DAO Team Safe"""
    safe_address = Address("0xA03be496e67Ec29bC62F01a428683D7F9c204930")
    app_hash = "Qme49gESuwpSvwANmEqo34yfCkzyQehooJ5yL7aHmKJnpZ"
    return (
        f"https://gnosis-safe.io/app/eth:{safe_address}"
        f"/apps?appUrl=https://cloudflare-ipfs.com/ipfs/{app_hash}/"
    )


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
        return self.value


@dataclass
class Transfer:
    """Total amount reimbursed for accounting period"""

    token_type: TokenType
    # Safe airdrop uses null address for native asset transfers
    token_address: Optional[Address]
    receiver: Address
    # safe-airdrop uses float amounts!
    amount: float

    @classmethod
    def from_dict(cls, obj: dict[str, str]) -> Transfer:
        """Converts Dune data dict to object with types"""
        token_type = TokenType.from_str(obj["token_type"])
        token_address = obj["token_address"]
        if token_type == TokenType.NATIVE and token_address is not None:
            raise ValueError("Native transfers must have null token_address")
        if token_type == TokenType.ERC20 and token_address is None:
            raise ValueError("ERC20 transfers must have valid token_address")

        return cls(
            token_type=token_type,
            token_address=Address(token_address)
            if token_type != TokenType.NATIVE
            else None,
            receiver=Address(obj["receiver"]),
            amount=float(obj["amount"]),
        )

    def add_slippage(self, slippage: SolverSlippage) -> None:
        """Adds Adjusts Transfer amount by Slippage amount"""
        assert self.receiver == slippage.solver_address, "receiver != solver"
        adjustment = slippage.amount_wei / 10**18
        print(
            f"Adjusting {self.receiver}({slippage.solver_name}) "
            f"transfer by {adjustment:.5f} (slippage)"
        )
        new_amount = self.amount + adjustment
        if new_amount <= 0:
            raise ValueError(f"Invalid adjustment {self} by {adjustment}")
        self.amount = new_amount

    def merge(self, other: Transfer) -> Transfer:
        """
        Merge two transfers (acts like addition)
        if all fields except amount are equal, returns a transfer who amount is the sum
        """
        merge_requirements = [
            self.receiver == other.receiver,
            self.token_type == other.token_type,
            self.token_address == other.token_address,
        ]
        if all(merge_requirements):
            return Transfer(
                token_type=self.token_type,
                token_address=self.token_address,
                receiver=self.receiver,
                amount=self.amount + other.amount,
            )
        raise ValueError(
            f"Can't merge tokens {self}, {other}. "
            f"Requirements met {merge_requirements}"
        )

    def __str__(self) -> str:
        if self.token_type == TokenType.NATIVE:
            return f"TransferETH(receiver={self.receiver}, amount={self.amount})"
        if self.token_type == TokenType.ERC20:
            return (
                f"Transfer("
                f"token_address={self.token_address}, "
                f"receiver={self.receiver}, "
                f"amount={self.amount})"
            )
        raise ValueError(f"Invalid Token Type {self.token_type}")


class Overdraft:
    def __init__(
        self, transfer: Transfer, slippage: SolverSlippage, period: AccountingPeriod
    ):
        assert transfer.token_type == TokenType.NATIVE
        overdraft = transfer.amount * 10**18 + slippage.amount_wei
        assert overdraft < 0, "This is why we are here."

        eth_amount = abs(overdraft) / 10**18
        self.period = period
        self.name = slippage.solver_name
        self.account = slippage.solver_address
        self.eth = eth_amount

    def __str__(self):
        return (
            f"Overdraft(\n"
            f"    solver={self.name}({self.account}),\n"
            f"    period={self.period},\n"
            f"    owed={self.eth} ETH\n"
            f")"
        )


def get_transfers(dune: DuneAPI, period: AccountingPeriod) -> list[Transfer]:
    """Fetches and returns slippage-adjusted Transfers for solver reimbursement"""
    query = DuneQuery.from_environment(
        raw_sql=open_query("./queries/period_transfers.sql"),
        network=Network.MAINNET,
        name="ETH Reimbursement & COW Rewards",
        parameters=[
            QueryParameter.date_type("StartTime", period.start),
            QueryParameter.date_type("EndTime", period.end),
            QueryParameter.number_type("PerBatchReward", COW_PER_BATCH),
            QueryParameter.number_type("PerTradeReward", COW_PER_TRADE),
        ],
    )
    reimbursements_and_rewards = dune.fetch(query)

    negative_slippage = get_period_slippage(dune, period).negative
    indexed_slippage = index_by(negative_slippage, "solver_address")
    cow_redirects = get_vouches(dune, period.end)

    results = []
    overdrafts: list[Overdraft] = []
    for row in reimbursements_and_rewards:
        transfer = Transfer.from_dict(row)
        solver = transfer.receiver
        slippage: Optional[SolverSlippage] = indexed_slippage.get(solver)
        if transfer.token_type == TokenType.NATIVE and slippage is not None:
            try:
                transfer.add_slippage(slippage)
            except ValueError as err:
                print(
                    f"Slippage for {slippage.solver_address}({slippage.solver_name}) "
                    f"exceeds reimbursement: {err} \n"
                    f"Excluding payout and appending excess to overdraft"
                )
                overdrafts.append(Overdraft(transfer, slippage, period))
                continue
        elif transfer.token_address == COW_TOKEN and solver in cow_redirects:
            # Redirect COW rewards to reward target specific by VouchRegistry
            redirect_address = cow_redirects[solver].reward_target
            print(f"Redirecting solver {solver} COW tokens to {redirect_address}")
            transfer.receiver = redirect_address

        results.append(transfer)
    if overdrafts:
        print("Additional owed", "\n".join(map(str, overdrafts)))
    return results


def consolidate_transfers(transfer_list: list[Transfer]) -> list[Transfer]:
    """
    Removes redundancy of a transfer list by consolidating _duplicate transfers_.
    Duplicates defined as transferring the same token to one recipient multiple times.
    This optimizes gas cost of multiple transfers.
    """

    transfer_dict: dict[tuple, Transfer] = {}
    for transfer in transfer_list:
        key = (transfer.receiver, transfer.token_type, transfer.token_address)
        if key in transfer_dict:
            transfer_dict[key] = transfer_dict[key].merge(transfer)
        else:
            transfer_dict[key] = transfer
    return sorted(
        transfer_dict.values(),
        key=lambda t: (-t.amount, t.receiver, t.token_address),
    )


def dashboard_url(period: AccountingPeriod) -> str:
    """Constructs Solver Accounting Dashboard URL for Period"""
    base = "https://dune.com/gnosis.protocol/"
    slug = "CoW-Protocol:-Solver-Accounting"
    query = f"?StartTime={period.start}&EndTime={period.end}"
    return base + urllib.parse.quote_plus(slug + query, safe="=&?")


if __name__ == "__main__":
    dune_connection, accounting_period = generic_script_init(
        description="Fetch Complete Reimbursement"
    )
    print(
        f"While you are waiting, The data being compiled here can be visualized at\n"
        f"{dashboard_url(accounting_period)}\n"
    )
    detect_unusual_slippage(dune=dune_connection, period=accounting_period)
    transfers = consolidate_transfers(
        get_transfers(
            dune=dune_connection,
            period=accounting_period,
        )
    )
    write_to_csv(
        data_list=transfers,
        outfile=File(name=f"transfers-{accounting_period}.csv"),
    )
    eth_total = sum(t.amount for t in transfers if t.token_type == TokenType.NATIVE)
    cow_total = sum(t.amount for t in transfers if t.token_type == TokenType.ERC20)

    print(
        f"Total ETH Funds needed: {eth_total}\n"
        f"Total COW Funds needed: {cow_total}\n"
        f"Please cross check these results with the dashboard linked above.\n "
        f"For solver payouts, paste the transfer file CSV Airdrop at:\n"
        f"{safe_url()}"
    )
