"""Logic for Post CIP 20 Solver Payout Calculation"""

from __future__ import annotations

import logging
from dataclasses import dataclass
from datetime import datetime, timedelta
from fractions import Fraction
from functools import reduce

import pandas
from dune_client.types import Address
from pandas import DataFrame, Series

from src.config import AccountingConfig
from src.fetch.dune import DuneFetcher
from src.fetch.prices import exchange_rate_atoms
from src.fetch.solver_info import SOLVER_INFO_COLUMNS, compute_solver_info
from src.fetch.rewards import REWARDS_COLUMNS, compute_rewards
from src.fetch.protocol_fees import PROTOCOL_FEES_COLUMNS, compute_protocol_fees
from src.fetch.partner_fees import compute_partner_fees
from src.fetch.buffer_accounting import (
    BUFFER_ACCOUNTING_COLUMNS,
    compute_buffer_accounting,
)
from src.logger import log_saver
from src.models.accounting_period import AccountingPeriod
from src.models.overdraft import Overdraft
from src.models.token import Token
from src.models.transfer import Transfer
from src.pg_client import MultiInstanceDBFetcher
from src.utils.print_store import Category


PAYMENT_COLUMNS = {
    "solver",
    "primary_reward_eth",
    "primary_reward_cow",
    "quote_reward_cow",
    "protocol_fee_eth",
    "network_fee_eth",
}
SLIPPAGE_COLUMNS = {
    "solver",
    "solver_name",
    "eth_slippage_wei",
}
REWARD_TARGET_COLUMNS = {"solver", "reward_target", "pool_address"}
SERVICE_FEE_COLUMNS = {"solver", "service_fee"}
ADDITIONAL_PAYMENT_COLUMNS = {"buffer_accounting_target", "reward_token_address"}

COMPLETE_COLUMNS = (
    PAYMENT_COLUMNS.union(SLIPPAGE_COLUMNS)
    .union(REWARD_TARGET_COLUMNS)
    .union(ADDITIONAL_PAYMENT_COLUMNS)
)
NUMERICAL_COLUMNS = [
    "primary_reward_eth",
    "primary_reward_cow",
    "quote_reward_cow",
    "protocol_fee_eth",
]

SOLVER_PAYOUTS_COLUMNS = [
    "solver",
    "primary_reward_eth",
    "primary_reward_cow",
    "quote_reward_cow",
    "protocol_fee_eth",
    "network_fee_eth",
    "slippage_eth",
]
PARTNER_PAYOUTS_COLUMNS = ["partner", "partner_fee_eth", "partner_fee_tax"]


@dataclass
class PeriodPayouts:
    """Dataclass to keep track of reimbursements, rewards and solver overdrafts"""

    overdrafts: list[Overdraft]
    # ETH Reimbursements & COW Rewards
    transfers: list[Transfer]


class RewardAndPenaltyDatum:  # pylint: disable=too-many-instance-attributes
    """
    All pertinent information and functionality related to individual solver payout (or overdraft)
    """

    def __init__(  # pylint: disable=too-many-arguments
        self,
        solver: Address,
        solver_name: str,
        reward_target: Address,  # recipient address of rewards
        buffer_accounting_target: Address,  # recipient address of net buffer changes
        primary_reward_eth: int,
        slippage_eth: int,
        primary_reward_cow: int,
        quote_reward_cow: int,
        service_fee: Fraction,
        reward_token_address: Address,
    ):

        assert quote_reward_cow >= 0, "invalid quote_reward_cow"

        self.solver = solver
        self.solver_name = solver_name
        self.reward_target = reward_target
        self.buffer_accounting_target = buffer_accounting_target
        self.slippage_eth = slippage_eth
        self.primary_reward_eth = primary_reward_eth
        self.primary_reward_cow = primary_reward_cow
        self.quote_reward_cow = quote_reward_cow
        self.service_fee = service_fee
        self.reward_token_address = reward_token_address

    @classmethod
    def from_series(cls, frame: Series) -> RewardAndPenaltyDatum:
        """Constructor from row in Dataframe"""
        slippage = int(frame["slippage_eth"]) + int(frame["network_fee_eth"])
        solver = frame["solver"]
        reward_target = frame["reward_target"]
        if reward_target is None:
            logging.warning(f"Solver {solver} without reward_target. Using solver")
            reward_target = solver

        buffer_accounting_target = frame["buffer_accounting_target"]
        if buffer_accounting_target is None:
            logging.warning(
                f"Solver {solver} without buffer_accounting_target. Using solver"
            )
            buffer_accounting_target = solver

        return cls(
            solver=Address(solver),
            solver_name=frame["solver_name"],
            reward_target=Address(reward_target),
            buffer_accounting_target=Address(buffer_accounting_target),
            slippage_eth=slippage,
            primary_reward_eth=int(frame["primary_reward_eth"]),
            primary_reward_cow=int(frame["primary_reward_cow"]),
            quote_reward_cow=int(frame["quote_reward_cow"]),
            service_fee=Fraction(frame["service_fee"]),
            reward_token_address=Address(frame["reward_token_address"]),
        )

    def total_outgoing_eth(self) -> int:
        """Total outgoing amount (including slippage) for the payout."""
        return self.total_eth_reward() + self.slippage_eth

    def total_cow_reward(self) -> int:
        """Total outgoing COW token reward"""
        return int(self.reward_scaling() * self.primary_reward_cow)

    def total_eth_reward(self) -> int:
        """Total outgoing ETH reward"""
        return int(self.reward_scaling() * self.primary_reward_eth)

    def reward_scaling(self) -> Fraction:
        """Scaling factor for service fee
        The reward is multiplied by this factor"""
        return 1 - self.service_fee

    def total_service_fee(self) -> Fraction:
        """Total service fee charged from rewards"""
        return self.service_fee * (self.primary_reward_cow + self.quote_reward_cow)

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
        quote_reward_cow = int(self.reward_scaling() * self.quote_reward_cow)
        result = []
        if quote_reward_cow > 0:
            result.append(
                Transfer(
                    token=Token(self.reward_token_address),
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
            # = self.payment_eth + self.slippage_eth
            # = self.total_outgoing_eth()
            # >= 0 (because not self.is_overdraft())
            try:
                result.append(
                    Transfer(
                        token=None,
                        recipient=self.buffer_accounting_target,
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
                        token=Token(self.reward_token_address),
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
                    recipient=self.buffer_accounting_target,
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
                    token=Token(self.reward_token_address),
                    recipient=self.reward_target,
                    amount_wei=total_cow_reward,
                )
            )
        except AssertionError:
            logging.warning(
                f"Invalid COW Transfer {self.solver} with amount={total_cow_reward}"
            )

        return result


def prepare_transfers(
    solver_payouts: DataFrame,
    partner_payouts: DataFrame,
    period: AccountingPeriod,
    config: AccountingConfig,
) -> PeriodPayouts:
    """Create transfers from payout data."""

    assert set(SOLVER_PAYOUTS_COLUMNS).issubset(set(solver_payouts.columns))
    assert set(PARTNER_PAYOUTS_COLUMNS).issubset(set(partner_payouts.columns))

    overdrafts: list[Overdraft] = []
    transfers: list[Transfer] = []
    for _, payment in solver_payouts.iterrows():
        payout_datum = RewardAndPenaltyDatum.from_series(payment)
        if payout_datum.is_overdraft():
            overdraft = Overdraft(
                period=period,
                account=payout_datum.solver,
                name=payout_datum.solver_name,
                wei=-int(payout_datum.total_outgoing_eth()),
            )
            print(f"Solver Overdraft! {overdraft}")
            overdrafts.append(overdraft)
        transfers += payout_datum.as_payouts()

    total_protocol_fee = int(solver_payouts["protocol_fee_eth"].sum())
    total_partner_fee = int(partner_payouts["partner_fee_eth"].sum())
    total_partner_fee_taxed = sum(
        int(row["partner_fee_eth"] * (1 - row["partner_fee_tax"]))
        for _, row in partner_payouts.iterrows()
    )
    total_partner_fee_tax = total_partner_fee - total_partner_fee_taxed

    net_protocol_fee = total_protocol_fee - total_partner_fee

    if net_protocol_fee > 0:
        transfers.append(
            Transfer(
                token=None,
                recipient=config.protocol_fee_config.protocol_fee_safe,
                amount_wei=net_protocol_fee,
            )
        )
    if total_partner_fee_tax > 0:
        transfers.append(
            Transfer(
                token=None,
                recipient=config.protocol_fee_config.protocol_fee_safe,
                amount_wei=total_partner_fee_tax,
            )
        )
    for _, row in partner_payouts.iterrows():
        partner = row["partner"]
        partner_fee = int(row["partner_fee_eth"] * (1 - row["partner_fee_tax"]))
        assert partner_fee >= 0, f"Can't construct negative transfer of {partner_fee}"
        if partner_fee > 0:
            transfers.append(
                Transfer(
                    token=None,
                    recipient=Address(partner),
                    amount_wei=partner_fee,
                )
            )

    return PeriodPayouts(overdrafts, transfers)


def fetch_exchange_rate(period_end: datetime, config: AccountingConfig) -> Fraction:
    """Fetch exchange rate for converting the native token to COW."""
    reward_token = config.reward_config.reward_token_address
    native_token = Address(config.payment_config.weth_address)
    price_day = period_end - timedelta(days=1)
    return exchange_rate_atoms(native_token, reward_token, price_day)


def validate_df_columns(
    solver_info: DataFrame,
    rewards: DataFrame,
    protocol_fees: DataFrame,
    buffer_accounting: DataFrame,
) -> None:
    """Validate data frame columns.
    Since we are working with dataframes rather than concrete objects,
    we validate that the expected columns/fields are available within our datasets.
    """
    assert set(solver_info.columns) == set(
        SOLVER_INFO_COLUMNS
    ), f"Solver info validation failed with columns: {set(solver_info.columns)}"
    assert set(rewards.columns) == set(
        REWARDS_COLUMNS
    ), f"Rewards validation failed with columns: {set(rewards.columns)}"
    assert set(protocol_fees.columns) == set(
        PROTOCOL_FEES_COLUMNS
    ), f"Protocol fee validation failed with columns: {set(protocol_fees.columns)}"
    assert set(buffer_accounting.columns) == set(
        BUFFER_ACCOUNTING_COLUMNS
    ), f"Buffer accounting validation failed with columns: {set(buffer_accounting.columns)}"


def normalize_address_field(frame: DataFrame, column_name: str) -> None:
    """Lower-cases column_name field"""
    frame[column_name] = frame[column_name].str.lower()


def compute_solver_payouts(
    solver_info: DataFrame,
    rewards: DataFrame,
    protocol_fees: DataFrame,
    buffer_accounting: DataFrame,
) -> DataFrame:
    """Combines solver accounting data into one payment dataframe."""
    # 1. Validate data
    validate_df_columns(solver_info, rewards, protocol_fees, buffer_accounting)

    # 2. Normalize Join Column (and Ethereum Address Field)
    join_column = "solver"
    normalize_address_field(solver_info, join_column)
    normalize_address_field(rewards, join_column)
    normalize_address_field(protocol_fees, join_column)
    normalize_address_field(buffer_accounting, join_column)

    # 3. Merge data
    solver_payouts = reduce(
        lambda left, right: left.merge(
            right,
            how="outer",
            on="solver",
            validate="one_to_one",
            sort=True,
        ),
        [rewards, protocol_fees, buffer_accounting],
    ).merge(solver_info, how="left", on="solver")

    # 4. Set default values
    solver_payouts["primary_reward_eth"] = solver_payouts["primary_reward_eth"].fillna(
        0
    )
    solver_payouts["slippage_eth"] = solver_payouts["slippage_eth"].fillna(0)
    solver_payouts["protocol_fee_eth"] = solver_payouts["protocol_fee_eth"].fillna(0)
    solver_payouts["network_fee_eth"] = solver_payouts["network_fee_eth"].fillna(0)
    solver_payouts["service_fee"] = solver_payouts["service_fee"].fillna(Fraction(0, 1))  # type: ignore

    return solver_payouts


def summarize_payments(solver_payouts: DataFrame, partner_payouts: DataFrame):
    performance_reward = solver_payouts["primary_reward_cow"].sum()
    quote_reward = solver_payouts["quote_reward_cow"].sum()
    protocol_fee = solver_payouts["protocol_fee_eth"].sum()
    service_fee = sum(
        solver_payouts["service_fee"]
        * (solver_payouts["primary_reward_cow"] + solver_payouts["quote_reward_cow"])
    )
    partner_fee = partner_payouts["partner_fee_eth"].sum()
    partner_fee_taxed = sum(
        row["partner_fee_eth"] * (1 - row["partner_fee_tax"])
        for _, row in partner_payouts.iterrows()
    )
    partner_fee_tax = partner_fee - partner_fee_taxed

    print(
        "Payment breakdown:\n"
        f"Performance Reward (before fee): {performance_reward / 10 ** 18:.4f}\n"
        f"Quote Reward (before fee): {quote_reward / 10 ** 18:.4f}\n"
        f"COW DAO Service Fees: {service_fee / 10 ** 18:.4f}\n",
        f"Protocol Fees (before partner fees): {protocol_fee / 10 ** 18:.4f}\n"
        f"Partner Fees (before tax): {partner_fee / 10 ** 18:.4f}\n"
        f"Partner Fees Tax: {partner_fee_tax / 10 ** 18:.4f}\n",
    )


def construct_payouts(
    orderbook: MultiInstanceDBFetcher,
    dune: DuneFetcher,
    ignore_slippage_flag: bool,
    config: AccountingConfig,
) -> list[Transfer]:
    """Workflow of solver reward payout logic post-CIP27"""
    # pylint: disable-msg=too-many-locals

    # fetch data
    # TODO: move data fetching into respective files for
    quote_rewards_df = orderbook.get_quote_rewards(dune.start_block, dune.end_block)
    batch_data = orderbook.get_solver_rewards(
        dune.start_block,
        dune.end_block,
        config.reward_config.batch_reward_cap_upper,
        config.reward_config.batch_reward_cap_lower,
    )
    service_fee_df = pandas.DataFrame(dune.get_service_fee_status())

    reward_target_df = pandas.DataFrame(dune.get_vouches())

    # fetch slippage only if configured to do so
    # otherwise set to an empty dataframe
    if config.buffer_accounting_config.include_slippage and not ignore_slippage_flag:
        slippage_df = pandas.DataFrame(dune.get_period_slippage())
        # TODO - After CIP-20 phased in, adapt query to return `solver` like all the others
        slippage_df = slippage_df.rename(columns={"solver_address": "solver"})
    else:
        slippage_df = DataFrame(columns=["solver", "eth_slippage_wei"])

    # fetch conversion price
    exchange_rate_native_to_cow = fetch_exchange_rate(dune.period.end, config)
    reward_token = config.reward_config.reward_token_address
    native_token = Address(config.payment_config.weth_address)
    price_day = dune.period.end - timedelta(days=1)
    exchange_rate_native_to_cow = exchange_rate_atoms(
        native_token, reward_token, price_day
    )

    # compute individual components of payments
    solver_info = compute_solver_info(
        reward_target_df,
        service_fee_df,
        config,
    )
    rewards = compute_rewards(
        batch_data,
        quote_rewards_df,
        exchange_rate_native_to_cow,
        config.reward_config,
    )
    protocol_fees = compute_protocol_fees(
        batch_data,
    )
    buffer_accounting = compute_buffer_accounting(batch_data, slippage_df)

    # combine into solver payouts and partner payouts
    solver_payouts = compute_solver_payouts(
        solver_info, rewards, protocol_fees, buffer_accounting
    )
    partner_payouts = compute_partner_fees(batch_data, config.protocol_fee_config)

    summarize_payments(solver_payouts, partner_payouts)

    # create transfers and overdrafts
    payouts = prepare_transfers(solver_payouts, partner_payouts, dune.period, config)

    for overdraft in payouts.overdrafts:
        log_saver.print(str(overdraft), Category.OVERDRAFT)
    return payouts.transfers
