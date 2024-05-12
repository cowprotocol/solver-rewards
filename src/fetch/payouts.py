"""Logic for Post CIP 38 Solver Payout Calculation"""

from __future__ import annotations

import logging
from dataclasses import dataclass
from datetime import timedelta

import pandas
from dune_client.types import Address
from pandas import DataFrame, Series

from src.constants import COW_TOKEN_ADDRESS
from src.fetch.fees import (
    compute_trade_fees,
    compute_protocol_partner_fees,
    PROTOCOL_FEE_SAFE,
)
from src.fetch.data_preprocessing import (
    preprocess_batch_data,
    preprocess_trade_data,
    preprocess_slippage_data,
    preprocess_reward_target,
)
from src.fetch.dune import DuneFetcher
from src.fetch.prices import eth_in_token, TokenId, token_in_eth, TokenConversion
from src.fetch.rewards import compute_solver_rewards
from src.fetch.slippage import compute_slippage
from src.models.accounting_period import AccountingPeriod
from src.models.overdraft import Overdraft
from src.models.token import Token
from src.models.transfer import Transfer
from src.pg_client import MultiInstanceDBFetcher
from src.utils.print_store import Category, PrintStore

BATCH_DATA_COLUMNS = {
    "winning_solver",
    "auction_id",
    "block_deadline",
    "winning_score",
    "reference_score",
    "tx_hash",
    "block_number",
    "log_index",
    "effective_gas_price",
    "gas_used",
    "surplus",
    "fee",
    "participating_solvers",
}
TRADE_DATA_COLUMNS = {
    "winning_solver",
    "auction_id",
    "tx_hash",
    "order_uid",
    "kind",
    "partially_fillable",
    "sell_token",
    "buy_token",
    "limit_sell_amount",
    "limit_buy_amount",
    "app_data",
    "quote_sell_amount",
    "quote_buy_amount",
    "quote_gas_amount",
    "quote_gas_price",
    "quote_sell_token_price",
    "quote_solver",
    "sell_amount",
    "buy_amount",
    "observed_fee",
    "sell_token_native_price",
    "buy_token_native_price",
}
SLIPPAGE_DATA_COLUMNS = {
    "solver_address",
    "solver_name",
    "eth_slippage_wei",
}
REWARD_TARGET_COLUMNS = {"solver", "reward_target"}

SOLVER_REWARDS_COLUMNS = {
    "solver",
    "solver_name",
    "reward_target",
    "primary_reward_eth",
    "secondary_reward_eth",
    "slippage_eth",
    "primary_reward_cow",
    "secondary_reward_cow",
    "quote_reward_cow",
}
PROTOCOL_FEE_COLUMNS = {
    "recipient",
    "fee_eth",
    "fee_cow",
    "from_partner_fee",
}


@dataclass
class PeriodPayouts:
    """Dataclass to keep track of solver payments and overdrafts"""

    overdrafts: list[Overdraft]
    # COW rewards, ETH slippage, ETH protocol and parnet fees
    transfers: list[Transfer]


class RewardAndSlippageDatum:  # pylint: disable=too-many-instance-attributes
    """
    All pertinent information and functionality related to individual solver payout (or overdraft)
    """

    def __init__(  # pylint: disable=too-many-arguments
        self,
        solver: Address,
        solver_name: str,
        reward_target: Address,
        primary_reward_eth: int,
        secondary_reward_eth: int,
        slippage_eth: int,
        primary_reward_cow: int,
        secondary_reward_cow: int,
        quote_reward_cow: int,
    ):
        assert secondary_reward_eth >= 0, "invalid secondary_reward_eth"
        assert secondary_reward_cow >= 0, "invalid secondary_reward_cow"
        assert quote_reward_cow >= 0, "invalid quote_reward_cow"

        self.solver = solver
        self.solver_name = solver_name
        self.reward_target = reward_target
        self.slippage_eth = slippage_eth
        self.primary_reward_eth = primary_reward_eth
        self.primary_reward_cow = primary_reward_cow
        self.secondary_reward_eth = secondary_reward_eth
        self.secondary_reward_cow = secondary_reward_cow
        self.quote_reward_cow = quote_reward_cow

    @classmethod
    def from_series(cls, frame: Series) -> RewardAndSlippageDatum:
        """Constructor from row in Dataframe"""

        solver = frame["solver"]
        reward_target = frame["reward_target"]
        if reward_target is None:
            logging.warning(f"solver {solver} without reward_target. Using solver")
            reward_target = solver

        return cls(
            solver=Address(solver),
            solver_name=frame["solver_name"],
            reward_target=Address(reward_target),
            slippage_eth=frame["slippage_eth"],
            primary_reward_eth=int(frame["primary_reward_eth"]),
            primary_reward_cow=int(frame["primary_reward_cow"]),
            secondary_reward_eth=int(frame["secondary_reward_eth"]),
            secondary_reward_cow=int(frame["secondary_reward_cow"]),
            quote_reward_cow=int(frame["quote_reward_cow"]),
        )

    def total_outgoing_eth(self) -> int:
        """Total outgoing amount (including slippage) for the payout."""
        return self.primary_reward_eth + self.secondary_reward_eth + self.slippage_eth

    def total_cow_reward(self) -> int:
        """Total outgoing COW token reward"""
        return self.primary_reward_cow + self.secondary_reward_cow

    def total_eth_reward(self) -> int:
        """Total outgoing ETH reward"""
        return self.primary_reward_eth + self.secondary_reward_eth

    def is_overdraft(self) -> bool:
        """
        True if the solver's complete combined data results in a net negative
        """
        return self.total_outgoing_eth() < 0

    def as_payouts(self) -> list[Transfer]:
        """
        Isolating the logic of how solvers are paid out according to their
            execution costs, rewards and slippage
        """
        quote_reward_cow = self.quote_reward_cow
        result = []
        if quote_reward_cow > 0:
            result.append(
                Transfer(
                    token=Token(COW_TOKEN_ADDRESS),
                    recipient=self.reward_target,
                    amount_wei=quote_reward_cow,
                )
            )
        if self.is_overdraft():
            return result

        total_eth_reward = int(self.total_eth_reward())
        total_cow_reward = int(self.total_cow_reward())

        reimbursement_eth = int(self.slippage_eth)
        # We do not have access to token conversion here, but we do have other converted values
        # x_eth:x_cow = y_eth:y_cow --> y_cow = y_eth * x_cow / x_eth
        reimbursement_cow = (
            (reimbursement_eth * total_cow_reward) // total_eth_reward
            if total_eth_reward != 0
            else 0
        )

        if reimbursement_eth > 0 > total_cow_reward:
            # If the total payment is positive but the total rewards are negative,
            # pay the total payment in ETH. The total payment corresponds to reimbursement,
            # reduced by the negative reward.
            # Note that;
            # reimbursement_eth + reward_eth
            # = self.total_eth_reward() + self.exec_cost + self.slippage_eth
            # = self.payment_eth + self.secondary_reward_eth + self.slippage_eth
            # = self.total_outgoing_eth()
            # >= 0 (because not self.is_overdraft())
            try:
                result.append(
                    Transfer(
                        token=None,
                        recipient=self.solver,
                        amount_wei=reimbursement_eth + total_eth_reward,
                    )
                )
            except AssertionError:
                logging.warning(
                    f"Invalid ETH Transfer {self.solver} "
                    f"with amount={reimbursement_eth + total_eth_reward}"
                )

            return result

        if reimbursement_eth < 0 < total_cow_reward:
            # If the total payment is positive but the total reimbursement is negative,
            # pay the total payment in COW. The total payment corresponds to a payment of rewards,
            # reduced by the negative reimbursement.
            try:
                result.append(
                    Transfer(
                        token=Token(COW_TOKEN_ADDRESS),
                        recipient=self.reward_target,
                        amount_wei=reimbursement_cow + total_cow_reward,
                    )
                )
            except AssertionError:
                logging.warning(
                    f"Invalid COW Transfer {self.solver} "
                    f"with amount={reimbursement_cow + total_cow_reward}"
                )

            return result

        try:
            result.append(
                Transfer(
                    token=None,
                    recipient=self.solver,
                    amount_wei=reimbursement_eth,
                )
            )
        except AssertionError:
            logging.warning(
                f"Invalid ETH Transfer {self.solver} with amount={reimbursement_eth}"
            )
        try:
            result.append(
                Transfer(
                    token=Token(COW_TOKEN_ADDRESS),
                    recipient=self.reward_target,
                    amount_wei=total_cow_reward,
                )
            )
        except AssertionError:
            logging.warning(
                f"Invalid COW Transfer {self.solver} with amount={total_cow_reward}"
            )

        return result


class ProtocolFeeDatum:
    """
    All pertinent information and functionality related to individual protocol or partner fee
    payment
    """

    def __init__(
        self,
        recipient: Address,
        fee_eth: int,
        fee_cow: int,
        from_partner_fee: bool,
    ):
        assert fee_eth >= 0, "invalid fee_eth"
        assert fee_cow >= 0, "invalid fee_cow"

        self.recipient = recipient
        self.fee_eth = fee_eth
        self.fee_cow = fee_cow
        self.from_partner_fee = from_partner_fee

    @classmethod
    def from_series(cls, frame: Series) -> ProtocolFeeDatum:
        """Constructor from row in Dataframe"""

        return cls(
            recipient=Address(frame["recipient"]),
            fee_eth=int(frame["fee_eth"]),
            fee_cow=int(frame["fee_cow"]),
            from_partner_fee=frame["from_partner_fee"],
        )

    def as_payout(self) -> Transfer:
        """Create transfare of protocol fees"""
        return Transfer(
            token=None,
            recipient=self.recipient,
            amount_wei=self.fee_eth,
        )


def prepare_transfers(
    solver_rewards_df: DataFrame,
    protocol_partner_fees_df: DataFrame,
    period: AccountingPeriod,
) -> PeriodPayouts:
    """Convert payment data from DataFramet to payouts."""
    validate_output_columns(solver_rewards_df, protocol_partner_fees_df)

    overdrafts: list[Overdraft] = []
    transfers: list[Transfer] = []
    for _, payment in solver_rewards_df.iterrows():
        reward_payout_datum = RewardAndSlippageDatum.from_series(payment)
        if reward_payout_datum.is_overdraft():
            overdraft = Overdraft(
                period=period,
                account=reward_payout_datum.solver,
                name=reward_payout_datum.solver_name,
                wei=-int(reward_payout_datum.total_outgoing_eth()),
            )
            print(f"Solver Overdraft! {overdraft}")
            overdrafts.append(overdraft)
        transfers += reward_payout_datum.as_payouts()

    for _, payment in protocol_partner_fees_df.iterrows():
        fee_payout_datum = ProtocolFeeDatum.from_series(payment)
        transfers.append(fee_payout_datum.as_payout())

    return PeriodPayouts(overdrafts, transfers)


def validate_input_columns(
    batch_data_df: DataFrame,
    trade_data_df: DataFrame,
    slippage_data_df: DataFrame,
    reward_target_df: DataFrame,
) -> None:
    """
    Since we are working with dataframes rather than concrete objects,
    we validate that the expected columns/fields are available within our datasets.
    While it is ok for the input data to contain more columns,
    this method merely validates that the expected ones are there.
    """
    assert BATCH_DATA_COLUMNS.issubset(
        set(batch_data_df.columns)
    ), f"Batch data validation failed with columns: {set(batch_data_df.columns)}"
    assert TRADE_DATA_COLUMNS.issubset(
        set(trade_data_df.columns)
    ), f"Trade data validation failed with columns: {set(trade_data_df.columns)}"
    assert SLIPPAGE_DATA_COLUMNS.issubset(
        set(slippage_data_df.columns)
    ), f"Slippage data validation Failed with columns: {set(slippage_data_df.columns)}"
    assert REWARD_TARGET_COLUMNS.issubset(
        set(reward_target_df.columns)
    ), f"Reward Target validation Failed with columns: {set(reward_target_df.columns)}"


def validate_output_columns(
    solver_rewards_df: DataFrame,
    protocol_partner_fees_df: DataFrame,
) -> None:
    """
    Since we are working with dataframes rather than concrete objects,
    we validate that the expected columns/fields are available within our datasets.
    While it is ok for the input data to contain more columns,
    this method merely validates that the expected ones are there.
    """
    assert SOLVER_REWARDS_COLUMNS.issubset(
        set(solver_rewards_df.columns)
    ), f"Solver payment validation failed with columns: {set(solver_rewards_df.columns)}"
    assert PROTOCOL_FEE_COLUMNS.issubset(
        set(protocol_partner_fees_df.columns)
    ), f"Fee payment validation failed with columns: {set(protocol_partner_fees_df.columns)}"


def normalize_address_field(frame: DataFrame, column_name: str) -> None:
    """Lower-cases column_name field"""
    frame[column_name] = frame[column_name].str.lower()


def construct_payout_dataframes(
    batch_data_df: DataFrame,
    trade_data_df: DataFrame,
    slippage_data_df: DataFrame,
    reward_target_df: DataFrame,
    converter: TokenConversion,
) -> tuple[DataFrame, DataFrame]:
    """Method responsible for computing rewards for solvers.
    The result is two dataframes.
    The first dataframe contains payment information on a per solver basis.
    The second dataframe contains payment information for the protocol and partners."""

    # 1. Assert existence of required columns.
    validate_input_columns(
        batch_data_df, trade_data_df, slippage_data_df, reward_target_df
    )

    # 2. Compute rewards
    solver_rewards_df = compute_solver_rewards(batch_data_df, trade_data_df, converter)

    # 3. Compute protocol fees and partner fees
    # protocol fees per trade
    trade_fees_df = compute_trade_fees(trade_data_df)

    # protocol and partner fees per recipient
    protocol_partner_fees_df = compute_protocol_partner_fees(trade_fees_df, converter)

    # 4. Compute slippage
    slippage_df = compute_slippage(slippage_data_df, trade_fees_df)

    # 4. Combine rewards
    solver_rewards_and_slippage_df = combine_rewards_and_slippage(
        solver_rewards_df, slippage_df, reward_target_df
    )

    return solver_rewards_and_slippage_df, protocol_partner_fees_df


def combine_rewards_and_slippage(
    solver_rewards_df: DataFrame, slippage_df: DataFrame, reward_target_df: DataFrame
) -> DataFrame:
    """Combine rewards and slippage data"""
    solver_rewards_and_slippage_df = (
        solver_rewards_df.merge(slippage_df, on="solver", how="outer")
        .fillna(0)
        .merge(reward_target_df.drop("pool", axis=1), on="solver", how="left")
        .astype(object)
        .sort_values("solver")
    )
    return solver_rewards_and_slippage_df


def summarize_payments(
    solver_rewards_and_slippage_df: DataFrame,
    protocol_partner_fees_df: DataFrame,
    log_saver: PrintStore,
) -> None:
    """Summarize payments"""
    # pylint: disable=singleton-comparison
    performance_reward = solver_rewards_and_slippage_df.primary_reward_cow.sum()
    participation_reward = solver_rewards_and_slippage_df.secondary_reward_cow.sum()
    quote_reward = solver_rewards_and_slippage_df.quote_reward_cow.sum()
    protocol_fee = protocol_partner_fees_df[
        protocol_partner_fees_df["from_partner_fee"] == False
    ].fee_eth.sum()
    partner_fee_tax = protocol_partner_fees_df[
        (protocol_partner_fees_df["from_partner_fee"] == True)
        & (protocol_partner_fees_df["recipient"] == str(PROTOCOL_FEE_SAFE))
    ].fee_eth.sum()
    partner_fee = protocol_partner_fees_df[
        (protocol_partner_fees_df["from_partner_fee"] == True)
        & (protocol_partner_fees_df["recipient"] != str(PROTOCOL_FEE_SAFE))
    ].fee_eth.sum()
    log_saver.print(
        f"Performance Reward: {performance_reward / 10 ** 18:.4f}\n"
        f"Participation Reward: {participation_reward / 10 ** 18:.4f}\n"
        f"Quote Reward: {quote_reward / 10 ** 18:.4f}\n"
        f"Protocol Fees: {protocol_fee / 10 ** 18:.4f}\n"
        f"Partner Fees Tax: {partner_fee_tax / 10 ** 18:.4f}\n"
        f"Partner Fees: {partner_fee / 10 ** 18:.4f}\n",
        category=Category.TOTALS,
    )


def construct_payouts(
    dune: DuneFetcher, orderbook: MultiInstanceDBFetcher
) -> list[Transfer]:
    """Workflow of solver reward payout logic post-CIP27"""

    # fetch data
    batch_data_df = orderbook.get_batch_data(dune.start_block, dune.end_block)
    trade_data_df = orderbook.get_trade_data(dune.start_block, dune.end_block)
    slippage_data_df = pandas.DataFrame(dune.get_period_slippage())
    reward_target_df = pandas.DataFrame(dune.get_vouches())

    # pre-process data
    batch_data_df = preprocess_batch_data(batch_data_df)
    trade_data_df = preprocess_trade_data(trade_data_df)
    slippage_data_df = preprocess_slippage_data(slippage_data_df)
    reward_target_df = preprocess_reward_target(reward_target_df)

    # fetch prices
    price_day = dune.period.end - timedelta(days=1)
    reward_token = TokenId.COW
    converter = TokenConversion(
        eth_to_token=lambda t: eth_in_token(reward_token, t, price_day),
        token_to_eth=lambda t: token_in_eth(reward_token, t, price_day),
    )

    # create payment dataframes
    (
        solver_rewards_and_slippage_df,
        protocol_partner_fees_df,
    ) = construct_payout_dataframes(
        batch_data_df,
        trade_data_df,
        slippage_data_df,
        reward_target_df,
        converter,
    )

    # summary of payments
    summarize_payments(
        solver_rewards_and_slippage_df, protocol_partner_fees_df, dune.log_saver
    )

    # generate transfers and overdrafts
    payouts = prepare_transfers(
        solver_rewards_and_slippage_df,
        protocol_partner_fees_df,
        dune.period,
    )
    for overdraft in payouts.overdrafts:
        dune.log_saver.print(str(overdraft), Category.OVERDRAFT)
    return payouts.transfers
