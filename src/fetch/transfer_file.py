"""Script to generate the CSV Airdrop file for Solver Rewards over an Accounting Period"""
from __future__ import annotations

import urllib.parse
from dataclasses import dataclass
from datetime import timedelta
from enum import Enum
from typing import Optional

from duneapi.api import DuneAPI
from duneapi.file_io import File, write_to_csv
from duneapi.types import DuneQuery, QueryParameter, Network, Address
from duneapi.util import open_query

from src.fetch.period_slippage import SolverSlippage, get_period_slippage
from src.fetch.reward_targets import get_vouches, Vouch

from src.models import AccountingPeriod
from src.utils.dataset import index_by
from src.utils.prices import eth_in_token, TokenId, token_in_eth
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

    @classmethod
    def native(cls, receiver: str | Address, amount: str | float) -> Transfer:
        """Construct a native token transfer"""
        if isinstance(receiver, str):
            receiver = Address(receiver)
        return cls(
            token_type=TokenType.NATIVE,
            receiver=receiver,
            amount=float(amount),
            token_address=None,
        )

    @classmethod
    def erc20(
        cls, receiver: str | Address, amount: str | float, token: str | Address
    ) -> Transfer:
        """Construct an erc20 token transfer"""
        if isinstance(token, str):
            token = Address(token)
        if isinstance(receiver, str):
            receiver = Address(receiver)

        return cls(
            token_type=TokenType.ERC20,
            receiver=receiver,
            amount=float(amount),
            token_address=token,
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


# pylint: disable=too-few-public-methods
class SplitTransfers:
    """
    This class keeps the ERC20 and NATIVE token transfers Split.
    Technically we should have two additional classes one for each token type.
    """

    def __init__(self, period: AccountingPeriod, mixed_transfers: list[Transfer]):
        self.period = period
        self.unprocessed_native = []
        self.unprocessed_cow = []
        for transfer in mixed_transfers:
            if transfer.token_type == TokenType.NATIVE:
                self.unprocessed_native.append(transfer)
            elif transfer.token_type == TokenType.ERC20:
                self.unprocessed_cow.append(transfer)
            else:
                raise ValueError(f"Invalid token type! {transfer.token_type}")
        # Initialize empty overdraft
        self.overdrafts: dict[Address, Overdraft] = {}
        self.eth_transfers: list[Transfer] = []
        self.cow_transfers: list[Transfer] = []

    def _process_native_transfers(
        self, indexed_slippage: dict[Address, SolverSlippage]
    ) -> None:
        while self.unprocessed_native:
            transfer = self.unprocessed_native.pop(0)
            solver = transfer.receiver
            slippage: Optional[SolverSlippage] = indexed_slippage.get(solver)
            if slippage is not None:
                try:
                    transfer.add_slippage(slippage)
                except ValueError as err:
                    name, address = slippage.solver_name, slippage.solver_address
                    print(
                        f"Slippage for {address}({name}) exceeds reimbursement: {err}\n"
                        f"Excluding payout and appending excess to overdraft"
                    )
                    self.overdrafts[solver] = Overdraft.from_objects(
                        transfer, slippage, self.period
                    )
                    continue
            self.eth_transfers.append(transfer)

    def _process_token_transfers(self, cow_redirects: dict[Address, Vouch]) -> None:
        price_day = self.period.end - timedelta(days=1)
        while self.unprocessed_cow:
            transfer = self.unprocessed_cow.pop(0)
            solver = transfer.receiver
            # Remove the element if it exists (assuming it won't have to be reinserted)
            overdraft = self.overdrafts.pop(solver, None)
            if overdraft is not None:
                cow_deduction = eth_in_token(TokenId.COW, overdraft.eth, price_day)
                print(f"Deducting {cow_deduction} COW from reward for {solver}")
                transfer.amount -= cow_deduction
                if transfer.amount < 0:
                    print(
                        "Overdraft exceeds COW reward! "
                        "Excluding reward and updating overdraft"
                    )
                    overdraft.eth = token_in_eth(
                        TokenId.COW, abs(transfer.amount), price_day
                    )
                    # Reinsert since there is still an amount owed.
                    self.overdrafts[solver] = overdraft
                    continue
            if solver in cow_redirects:
                # Redirect COW rewards to reward target specific by VouchRegistry
                redirect_address = cow_redirects[solver].reward_target
                print(
                    f"Redirecting solver {solver} COW tokens "
                    f"({transfer.amount}) to {redirect_address}"
                )
                transfer.receiver = redirect_address
            self.cow_transfers.append(transfer)

    def process(
        self,
        indexed_slippage: dict[Address, SolverSlippage],
        cow_redirects: dict[Address, Vouch],
    ) -> list[Transfer]:
        """
        This is the public interface to construct the final transfer file based on
        raw (unpenalized) results, slippage penalty, redirected rewards and overdrafts.
        It is very important that the native token transfers are processed first,
        so that and overdraft from slippage can be carried over and deducted from
        the COW rewards.
        """
        self._process_native_transfers(indexed_slippage)
        self._process_token_transfers(cow_redirects)
        if self.overdrafts:
            print("Additional owed", "\n".join(map(str, self.overdrafts.values())))
        return self.cow_transfers + self.eth_transfers


@dataclass
class Overdraft:
    """
    Contains the data for a solver's overdraft;
    Namely, overdraft = |transfer - negative slippage| when the difference is negative
    """

    period: AccountingPeriod
    account: Address
    name: str
    eth: float

    @classmethod
    def from_objects(
        cls, transfer: Transfer, slippage: SolverSlippage, period: AccountingPeriod
    ) -> Overdraft:
        """Constructs an overdraft instance based on Transfer & Slippage"""
        assert transfer.receiver == slippage.solver_address
        assert transfer.token_type == TokenType.NATIVE
        overdraft = transfer.amount * 10**18 + slippage.amount_wei
        assert overdraft < 0, "This is why we are here."
        return cls(
            period=period,
            name=slippage.solver_name,
            account=slippage.solver_address,
            eth=abs(overdraft) / 10**18,
        )

    def __str__(self) -> str:
        return (
            f"Overdraft(solver={self.account}({self.name}),"
            f"period={self.period},owed={self.eth} ETH)"
        )


# pylint: enable=too-few-public-methods


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
    reimbursements_and_rewards = [Transfer.from_dict(t) for t in dune.fetch(query)]
    # TODO - Here we could also merge all the transfers with the merge data from below!
    split_transfers = SplitTransfers(period, reimbursements_and_rewards)

    negative_slippage = get_period_slippage(dune, period).negative

    # This mapping is in the form name -> (OldSolver, NewSolver)
    merge_data = {
        "prod-Otex": (
            "0x6fa201c3aff9f1e4897ed14c7326cf27548d9c35",
            "0xc9ec550bea1c64d779124b23a26292cc223327b6",
        ),
        "prod-Baseline": (
            "0x833f076d182123ca8dde2743045ea02957bd61ef",
            "0x3cee8c7d9b5c8f225a8c36e7d3514e1860309651",
        ),
        "prod-Naive": (
            "0x340185114f9d2617dc4c16088d0375d09fee9186",
            "0x7a0a8890d71a4834285efdc1d18bb3828e765c6a",
        ),
        "prod-DexCowAgg": (
            "0x2d15894fac906386ff7f4bd07fceac43fcf80c73",
            "0x6d1247b8acf4dfd5ff8cfd6c47077ddc43d4500e",
        ),
        "prod-ParaSwap": (
            "0x15f4c337122ec23859ec73bec00ab38445e45304",
            "0xe9ae2d792f981c53ea7f6493a17abf5b2a45a86b",
        ),
        "prod-Legacy": (
            "0xa6ddbd0de6b310819b49f680f65871bee85f517e",
            "0x0e8f282ce027f3ac83980e6020a2463f4c841264",
        ),
        "prod-PLM": (
            "0xe58c68679e7aab8ef83bf37e88b18eb1f6e30e22",
            "0x149d0f9282333681ee41d30589824b2798e9fb47",
        ),
        "prod-QuasiModo": (
            "0x77ec2a722c2393d3fd64617bbaf1499c713e616b",
            "0x731a0a8ab2c6fcad841e82d06668af7f18e34970",
        ),
        "prod-BalancerSOR": (
            "0xa97def4fbcba3b646dd169bc2eee40f0f3fe7771",
            "0xf7995b6b051166ea52218c37b8d03a2a6bbef3da",
        ),
        "prod-0x": (
            "0xe92f359e6f05564849afa933ce8f62b8007a1d5d",
            "0xda869be4adea17ad39e1dfece1bc92c02491504f",
        ),
        "prod-MIP": (
            "0xf2d21ad3c88170d4ae52bbbeba80cb6078d276f4",
            "0xe8ff24ec26bd46e0140d1824da44efad2a0920b5",
        ),
        "prod-1inch": (
            "0xde1c59bc25d806ad9ddcbe246c4b5e5505645718",
            "0xb20b86c4e6deeb432a22d773a221898bbbd03036",
        ),
    }
    indexed_slippage = index_by(negative_slippage, "solver_address")
    for name, (old, new) in merge_data.items():
        # Remove the old one.
        old_address, target = Address(old), Address(new)
        old_solver_slippage: SolverSlippage = indexed_slippage.pop(
            old_address, SolverSlippage.zero(address=old_address, name=name)
        )
        new_solver_slippage: SolverSlippage = indexed_slippage.pop(
            target, SolverSlippage.zero(address=target, name=name)
        )
        # Merge old with new.
        indexed_slippage[target] = new_solver_slippage.merge(
            old_solver_slippage, target
        )

    return split_transfers.process(
        indexed_slippage=index_by(negative_slippage, "solver_address"),
        cow_redirects=get_vouches(dune, period.end),
    )


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


def unusual_slippage_url(period: AccountingPeriod) -> str:
    """Returns a link to unusual slippage query for period"""
    base = "https://dune.com/queries/645559"
    query = f"?StartTime={period.start}&EndTime={period.end}"
    return base + urllib.parse.quote_plus(query, safe="=&?")


if __name__ == "__main__":
    dune_connection, accounting_period = generic_script_init(
        description="Fetch Complete Reimbursement"
    )
    print(
        f"While you are waiting, The data being compiled here can be visualized at\n"
        f"{dashboard_url(accounting_period)}"
    )
    print(
        f"In particular, please double check the batches with unusual slippage: "
        f"{unusual_slippage_url(accounting_period)}"
    )
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
