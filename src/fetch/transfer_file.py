"""
Script to generate the CSV Airdrop file for Solver Rewards over an Accounting Period
"""
from __future__ import annotations

import os
import ssl
import urllib.parse
from dataclasses import dataclass
from datetime import timedelta
from enum import Enum
from typing import Optional

import certifi
import pandas as pd
from duneapi.api import DuneAPI
from duneapi.file_io import File, write_to_csv
from duneapi.types import DuneQuery, QueryParameter, Network, Address
from duneapi.util import open_query
from eth_typing.encoding import HexStr
from eth_typing.ethpm import URI
from gnosis.eth.ethereum_client import EthereumClient
from gnosis.safe.multi_send import MultiSendOperation, MultiSendTx
from pandas import DataFrame
from slack.web.client import WebClient
from slack.web.slack_response import SlackResponse
from web3 import Web3

from src.constants import (
    ERC20_TOKEN,
    SAFE_ADDRESS,
    NETWORK,
    NODE_URL,
    AIRDROP_URL,
    SAFE_URL,
)
from src.fetch.orderbook_rewards import get_orderbook_rewards
from src.fetch.period_slippage import SolverSlippage, get_period_slippage
from src.fetch.reward_targets import get_vouches, Vouch
from src.fetch.risk_free_batches import get_risk_free_batches
from src.models import AccountingPeriod, Token
from src.multisend import post_multisend
from src.update.orderbook_rewards import push_user_generated_view, RewardQuery
from src.utils.dataset import index_by
from src.utils.prices import eth_in_token, TokenId, token_in_eth
from src.utils.print_store import PrintStore, Category
from src.utils.query_file import query_file
from src.utils.script_args import generic_script_init

log_saver = PrintStore()


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

    def add_slippage(self, slippage: SolverSlippage) -> None:
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
        Merge two transfers (acts like addition)
        if all fields except amount are equal, returns a transfer who amount is the sum
        """
        merge_requirements = [
            self.receiver == other.receiver,
            self.token == other.token,
        ]
        if all(merge_requirements):
            return Transfer(
                token=self.token,
                receiver=self.receiver,
                amount_wei=self.amount_wei + other.amount_wei,
            )
        raise ValueError(
            f"Can't merge tokens {self}, {other}. "
            f"Requirements met {merge_requirements}"
        )

    def as_multisend_tx(self) -> MultiSendTx:
        """Converts Transfer into encoded MultiSendTx bytes"""
        if self.token_type == TokenType.NATIVE:
            return MultiSendTx(
                operation=MultiSendOperation.CALL,
                to=self.receiver.address,
                value=self.amount_wei,
                data=HexStr("0x"),
            )
        if self.token_type == TokenType.ERC20:
            assert self.token is not None
            return MultiSendTx(
                operation=MultiSendOperation.CALL,
                to=str(self.token.address),
                value=0,
                data=ERC20_TOKEN.encodeABI(
                    fn_name="transfer", args=[self.receiver.address, self.amount_wei]
                ),
            )
        raise ValueError(f"Unsupported type {self.token_type}")

    def __str__(self) -> str:
        if self.token_type == TokenType.NATIVE:
            return f"TransferETH(receiver={self.receiver}, amount_wei={self.amount})"
        if self.token_type == TokenType.ERC20:
            return (
                f"Transfer("
                f"token_address={self.token}, "
                f"receiver={self.receiver}, "
                f"amount_wei={self.amount})"
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
    ) -> int:
        penalty_total = 0
        while self.unprocessed_native:
            transfer = self.unprocessed_native.pop(0)
            solver = transfer.receiver
            slippage: Optional[SolverSlippage] = indexed_slippage.get(solver)
            if slippage is not None:
                try:
                    transfer.add_slippage(slippage)
                    penalty_total += slippage.amount_wei
                except ValueError as err:
                    name, address = slippage.solver_name, slippage.solver_address
                    log_saver.print(
                        f"Slippage for {address}({name}) exceeds reimbursement: {err}\n"
                        f"Excluding payout and appending excess to overdraft",
                        category=Category.OVERDRAFT,
                    )
                    self.overdrafts[solver] = Overdraft.from_objects(
                        transfer, slippage, self.period
                    )
                    # Deduct entire transfer value.
                    penalty_total -= transfer.amount_wei
                    continue
            self.eth_transfers.append(transfer)
        return penalty_total

    def _process_token_transfers(self, cow_redirects: dict[Address, Vouch]) -> None:
        price_day = self.period.end - timedelta(days=1)
        while self.unprocessed_cow:
            transfer = self.unprocessed_cow.pop(0)
            solver = transfer.receiver
            # Remove the element if it exists (assuming it won't have to be reinserted)
            overdraft = self.overdrafts.pop(solver, None)
            if overdraft is not None:
                cow_deduction = eth_in_token(TokenId.COW, overdraft.wei, price_day)
                log_saver.print(
                    f"Deducting {cow_deduction} COW from reward for {solver}",
                    category=Category.OVERDRAFT,
                )
                transfer.amount_wei -= cow_deduction
                if transfer.amount_wei < 0:
                    log_saver.print(
                        "Overdraft exceeds COW reward! "
                        "Excluding reward and updating overdraft",
                        category=Category.OVERDRAFT,
                    )
                    overdraft.wei = token_in_eth(
                        TokenId.COW, abs(transfer.amount_wei), price_day
                    )
                    # Reinsert since there is still an amount owed.
                    self.overdrafts[solver] = overdraft
                    continue
            if solver in cow_redirects:
                # Redirect COW rewards to reward target specific by VouchRegistry
                redirect_address = cow_redirects[solver].reward_target
                log_saver.print(
                    f"Redirecting solver {solver} COW tokens "
                    f"({transfer.amount}) to {redirect_address}",
                    category=Category.REDIRECT,
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
        penalty_total = self._process_native_transfers(indexed_slippage)
        self._process_token_transfers(cow_redirects)
        log_saver.print(
            f"Total Slippage deducted (ETH): {penalty_total / 10**18}",
            category=Category.TOTALS,
        )
        if self.overdrafts:
            accounts_owing = "\n".join(map(str, self.overdrafts.values()))
            log_saver.print(
                f"Additional owed\n {accounts_owing}", category=Category.OVERDRAFT
            )
        return self.cow_transfers + self.eth_transfers


# pylint: enable=too-few-public-methods


@dataclass
class Overdraft:
    """
    Contains the data for a solver's overdraft;
    Namely, overdraft = |transfer - negative slippage| when the difference is negative
    """

    period: AccountingPeriod
    account: Address
    name: str
    wei: int

    @classmethod
    def from_objects(
        cls, transfer: Transfer, slippage: SolverSlippage, period: AccountingPeriod
    ) -> Overdraft:
        """Constructs an overdraft instance based on Transfer & Slippage"""
        assert transfer.receiver == slippage.solver_address
        assert transfer.token_type == TokenType.NATIVE
        overdraft = transfer.amount_wei + slippage.amount_wei
        assert overdraft < 0, "This is why we are here."
        return cls(
            period=period,
            name=slippage.solver_name,
            account=slippage.solver_address,
            wei=abs(overdraft),
        )

    @property
    def eth(self) -> float:
        """Returns amount in units"""
        return self.wei / 10**18

    def __str__(self) -> str:
        return (
            f"Overdraft(solver={self.account}({self.name}),"
            f"period={self.period},owed={self.eth} ETH)"
        )


def map_reward(
    amount: float,
    risk_free: bool,
    batch_contains_unsafe_liquidity: bool,
) -> float:
    """
    Converts orderbook rewards based on additional information of
    "risk_free" batches and (un)safe liquidity orders.
    - risk-free are batches contain only user and liquidity orders (i.e. no AMM interactions),
    - liquidity orders are further classified as being safe or unsafe;
        Examples: (unsafe) 0x and just in time orders which carry some revert risk
    """
    if amount > 0 and risk_free and not batch_contains_unsafe_liquidity:
        # Risk Free User Orders that are not contained in unsafe batches 37 COW tokens.
        return 37.0
    return amount


def unsafe_batches(order_df: DataFrame) -> set[str]:
    """
    Filters for tx_hashes corresponding to batches containing "unsafe"
    liquidity orders. These are identified from the order reward dataframe as
    entries with amount = 0 and safe_liquidity = False.
    """
    liquidity = order_df.loc[order_df["amount"] == 0]
    liquidity = liquidity.astype({"safe_liquidity": "boolean"})
    unsafe_liquidity = liquidity.loc[~liquidity["safe_liquidity"]]
    return set(unsafe_liquidity["tx_hash"])


def aggregate_orderbook_rewards(
    per_order_df: DataFrame, risk_free_transactions: set[str]
) -> DataFrame:
    """
    Takes rewards per order and adjusts them based on whether they were part of
    a risk-free settlement or not. After the new amount mapping is complete,
    the results are aggregated by solver as a sum of amounts and additional
    "transfer" related metadata is appended. The aggregated dataframe is returned.
    """

    unsafe_liquidity_batches = unsafe_batches(per_order_df)
    per_order_df["amount"] = per_order_df[
        ["amount", "tx_hash", "safe_liquidity"]
    ].apply(
        lambda x: map_reward(
            amount=x.amount,
            risk_free=x.tx_hash in risk_free_transactions,
            batch_contains_unsafe_liquidity=x.tx_hash in unsafe_liquidity_batches,
        ),
        axis=1,
    )
    result_agg = (
        per_order_df.groupby("solver")["amount"].agg(["count", "sum"]).reset_index()
    )
    del per_order_df  # We don't need this anymore!
    # Add token address to each column
    result_agg["token_address"] = "0xDEf1CA1fb7FBcDC777520aa7f396b4E015F497aB"
    # Rename columns to align with "Transfer" Object
    result_agg = result_agg.rename(
        columns={"sum": "amount", "count": "num_trades", "solver": "receiver"}
    )
    # Convert float amounts to WEI
    result_agg["amount"] = result_agg["amount"].apply(
        lambda x: Web3().toWei(x, "ether")
    )
    return result_agg


def get_cow_rewards(dune: DuneAPI, period: AccountingPeriod) -> list[Transfer]:
    """
    Fetches COW token rewards from orderbook database returning a list of Transfers
    """
    start_block, end_block = period.get_block_interval(dune)
    print(f"Fetching CoW Rewards for block interval {start_block}, {end_block}")
    per_order_df = get_orderbook_rewards(start_block, end_block)
    # Pushing the pre-adjusted orderbook rewards (right from the DB)
    push_user_generated_view(dune, period, per_order_df, RewardQuery.PER_ORDER)
    cow_rewards_df = aggregate_orderbook_rewards(
        per_order_df,
        risk_free_transactions=get_risk_free_batches(dune, period),
    )

    # Validation of results - using characteristics of results from two sources.
    dune_trade_counts = dune.fetch(
        query=DuneQuery.from_environment(
            raw_sql=open_query(query_file("dune_trade_counts.sql")),
            network=Network.MAINNET,
            name="Trade Counts",
            parameters=[
                QueryParameter.text_type("start_block", start_block),
                QueryParameter.text_type("end_block", end_block),
            ],
        )
    )
    # Number of trades per solver retrieved from orderbook agrees ethereum events.
    duplicates = pd.concat(
        [
            pd.DataFrame(dune_trade_counts),
            cow_rewards_df[["receiver", "num_trades"]].rename(
                columns={"receiver": "solver"}
            ),
        ]
    ).drop_duplicates(keep=False)

    assert len(duplicates) == 0, f"solver sets disagree: {duplicates}"

    # Write this to Dune Database (as a user generated view).
    push_user_generated_view(
        dune, period, data=cow_rewards_df, data_type=RewardQuery.AGGREGATE
    )
    return Transfer.from_dataframe(cow_rewards_df)


def get_eth_spent(dune: DuneAPI, period: AccountingPeriod) -> list[Transfer]:
    """
    Fetches ETH spent on successful settlements by all solvers during `period`
    """
    query = DuneQuery.from_environment(
        raw_sql=open_query(query_file("eth_spent.sql")),
        network=Network.MAINNET,
        name="ETH Reimbursement",
        parameters=[
            QueryParameter.date_type("StartTime", period.start),
            QueryParameter.date_type("EndTime", period.end),
        ],
    )
    return [Transfer.from_dict(t) for t in dune.fetch(query)]


def get_transfers(dune: DuneAPI, period: AccountingPeriod) -> list[Transfer]:
    """Fetches and returns slippage-adjusted Transfers for solver reimbursement"""
    reimbursements = get_eth_spent(dune, period)
    rewards = get_cow_rewards(dune, period)
    split_transfers = SplitTransfers(period, reimbursements + rewards)
    negative_slippage = get_period_slippage(dune, period).negative

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
        key = (transfer.receiver, transfer.token)
        if key in transfer_dict:
            transfer_dict[key] = transfer_dict[key].merge(transfer)
        else:
            transfer_dict[key] = transfer
    return sorted(
        transfer_dict.values(),
        key=lambda t: (-t.amount, t.receiver, t.token),
    )


def dashboard_url(period: AccountingPeriod) -> str:
    """Constructs Solver Accounting Dashboard URL for Period"""
    base = "https://dune.com/gnosis.protocol/"
    slug = "solver-rewards-accounting-v2"
    query = f"?StartTime={period.start}&EndTime={period.end}&PeriodHash={hash(period)}"
    return base + urllib.parse.quote_plus(slug + query, safe="=&?")


def unusual_slippage_url(period: AccountingPeriod) -> str:
    """Returns a link to unusual slippage query for period"""
    base = "https://dune.com/queries/645559"
    query = f"?StartTime={period.start}&EndTime={period.end}"
    return base + urllib.parse.quote_plus(query, safe="=&?")


def summary(transfers: list[Transfer]) -> str:
    """Summarizes transfers with totals"""
    eth_total = sum(t.amount_wei for t in transfers if t.token_type == TokenType.NATIVE)
    cow_total = sum(t.amount_wei for t in transfers if t.token_type == TokenType.ERC20)
    return (
        f"Total ETH Funds needed: {eth_total / 10 ** 18}\n"
        f"Total COW Funds needed: {cow_total / 10 ** 18}\n"
    )


def manual_propose(dune: DuneAPI, period: AccountingPeriod) -> None:
    """
    Entry point to manual creation of rewards payout transaction.
    This function generates the CSV transfer file to be pasted into the COW Safe app
    """
    print(
        f"Please double check the batches with unusual slippage: "
        f"{unusual_slippage_url(period)}"
    )
    transfers = consolidate_transfers(get_transfers(dune, period))
    write_to_csv(
        data_list=[CSVTransfer.from_transfer(t) for t in transfers],
        outfile=File(name=f"transfers-{period}.csv"),
    )
    print(summary(transfers))
    print(
        f"Please cross check these results with the dashboard linked above.\n "
        f"For solver payouts, paste the transfer file CSV Airdrop at:\n"
        f"{AIRDROP_URL}"
    )


def post_to_slack(
    slack_client: WebClient, channel: str, message: str, sub_messages: dict[str, str]
) -> None:
    """Posts message to slack channel and sub message inside thread of first message"""
    response = slack_client.chat_postMessage(
        channel=channel,
        text=message,
        # Do not show link preview!
        # https://api.slack.com/reference/messaging/link-unfurling
        unfurl_media=False,
    )
    # This assertion is only for type safety,
    # since previous function can also return a Future
    assert isinstance(response, SlackResponse)
    # Post logs in thread.
    for category, log in sub_messages.items():
        slack_client.chat_postMessage(
            channel=channel,
            format="mrkdwn",
            text=f"{category}:\n```{log}```",
            # According to https://api.slack.com/methods/conversations.replies
            thread_ts=response.get("ts"),
            unfurl_media=False,
        )


def auto_propose(
    dune: DuneAPI, slack_client: WebClient, period: AccountingPeriod, dry_run: bool
) -> None:
    """
    Entry point auto creation of rewards payout transaction.
    This function encodes the multisend of reward transfers and posts
    the transaction to the COW TEAM SAFE from the proposer account.
    """
    # Check for required env vars early
    # so not to wait for query execution to realize it's not available.
    signing_key = os.environ["PROPOSER_PK"]
    client = EthereumClient(URI(NODE_URL))

    transfers = consolidate_transfers(get_transfers(dune, period))
    log_saver.print(summary(transfers), category=Category.TOTALS)
    if not dry_run:
        nonce = post_multisend(
            safe_address=SAFE_ADDRESS,
            transfers=[t.as_multisend_tx() for t in transfers],
            network=NETWORK,
            signing_key=signing_key,
            client=client,
        )
        post_to_slack(
            slack_client,
            channel=os.environ["SLACK_CHANNEL"],
            message=(
                f"Solver Rewards transaction with nonce {nonce} pending signatures.\n"
                f"To sign and execute, visit:\n{SAFE_URL}\n"
                f"More details in thread"
            ),
            sub_messages=log_saver.get_values(),
        )


if __name__ == "__main__":
    args = generic_script_init(description="Fetch Complete Reimbursement")
    log_saver.print(
        f"The data being aggregated here is available for visualization at\n"
        f"{dashboard_url(args.period)}",
        category=Category.GENERAL,
    )
    if args.post_tx:
        auto_propose(
            dune=args.dune,
            slack_client=WebClient(
                token=os.environ["SLACK_TOKEN"],
                # https://stackoverflow.com/questions/59808346/python-3-slack-client-ssl-sslcertverificationerror
                ssl=ssl.create_default_context(cafile=certifi.where()),
            ),
            period=args.period,
            dry_run=args.dry_run,
        )
    else:
        manual_propose(args.dune, args.period)
