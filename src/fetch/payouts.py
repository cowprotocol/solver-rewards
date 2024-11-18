"""Logic for Post CIP 20 Solver Payout Calculation"""

from __future__ import annotations

import math
from dataclasses import dataclass
from datetime import timedelta
from fractions import Fraction
from typing import Callable

import numpy as np
import pandas
from dune_client.types import Address
from pandas import DataFrame, Series

from src.config import AccountingConfig
from src.fetch.dune import DuneFetcher
from src.fetch.prices import exchange_rate_atoms
from src.logger import log_saver, set_log
from src.models.accounting_period import AccountingPeriod
from src.models.overdraft import Overdraft
from src.models.token import Token
from src.models.transfer import Transfer
from src.pg_client import MultiInstanceDBFetcher
from src.utils.print_store import Category

log = set_log(__name__)

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
        slippage = (
            int(frame["eth_slippage_wei"])
            if not math.isnan(frame["eth_slippage_wei"])
            else 0
        )
        solver = frame["solver"]
        reward_target = frame["reward_target"]
        if reward_target is None:
            log.warning(f"Solver {solver} without reward_target. Using solver")
            reward_target = solver

        buffer_accounting_target = frame["buffer_accounting_target"]
        if buffer_accounting_target is None:
            log.warning(
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
                log.warning(
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
                log.warning(
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
            log.warning(
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
            log.warning(
                f"Invalid COW Transfer {self.solver} with amount={total_cow_reward}"
            )

        return result


@dataclass
class TokenConversion:
    """
    Data Structure containing token conversion methods.
    """

    eth_to_token: Callable


def extend_payment_df(
    pdf: DataFrame, converter: TokenConversion, config: AccountingConfig
) -> DataFrame:
    """
    Extending the basic columns returned by SQL Query with some after-math:
    - reward_eth as difference of payment and execution_cost
    - reward_cow as conversion from ETH to cow.
    """
    # Note that this can be negative!
    pdf["primary_reward_cow"] = pdf["primary_reward_eth"].apply(converter.eth_to_token)

    # Pandas has poor support for large integers, must cast the constant to float here,
    # otherwise the dtype would be inferred as int64 (which overflows).

    reward_per_quote = float(
        min(
            config.reward_config.quote_reward_cow,
            converter.eth_to_token(config.reward_config.quote_reward_cap_native),
        )
    )

    log.info(f"A reward of {reward_per_quote / 10**18:.4f} COW per quote is used.")
    pdf["quote_reward_cow"] = reward_per_quote * pdf["num_quotes"]

    for number_col in NUMERICAL_COLUMNS:
        pdf[number_col] = pandas.to_numeric(pdf[number_col])

    return pdf


def prepare_transfers(  # pylint: disable=too-many-arguments
    payout_df: DataFrame,
    period: AccountingPeriod,
    final_protocol_fee_wei: int,
    partner_fee_tax_wei: int,
    partner_fees_wei: dict[str, int],
    config: AccountingConfig,
) -> PeriodPayouts:
    """
    Manipulates the payout DataFrame to split into ETH and COW.
    Specifically, We deduct total_rewards by total_execution_cost (both initially in ETH)
    keep the execution cost in ETH and convert the difference to COW.
    """
    assert COMPLETE_COLUMNS.issubset(set(payout_df.columns))

    overdrafts: list[Overdraft] = []
    transfers: list[Transfer] = []
    for _, payment in payout_df.iterrows():
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

    if final_protocol_fee_wei > 0:
        transfers.append(
            Transfer(
                token=None,
                recipient=config.protocol_fee_config.protocol_fee_safe,
                amount_wei=final_protocol_fee_wei,
            )
        )
    if partner_fee_tax_wei > 0:
        transfers.append(
            Transfer(
                token=None,
                recipient=config.protocol_fee_config.protocol_fee_safe,
                amount_wei=partner_fee_tax_wei,
            )
        )
    for address in partner_fees_wei:
        amount_wei = partner_fees_wei[address]
        assert amount_wei >= 0, f"Can't construct negative transfer of {amount_wei}"
        if amount_wei > 0:
            transfers.append(
                Transfer(
                    token=None,
                    recipient=Address(address),
                    amount_wei=amount_wei,
                )
            )

    return PeriodPayouts(overdrafts, transfers)


def validate_df_columns(
    payment_df: DataFrame,
    slippage_df: DataFrame,
    reward_target_df: DataFrame,
    service_fee_df: DataFrame,
) -> None:
    """
    Since we are working with dataframes rather than concrete objects,
    we validate that the expected columns/fields are available within our datasets.
    While it is ok for the input data to contain more columns,
    this method merely validates that the expected ones are there.
    """
    assert PAYMENT_COLUMNS.issubset(
        set(payment_df.columns)
    ), f"Payment validation failed with columns: {set(payment_df.columns)}"
    assert SLIPPAGE_COLUMNS.issubset(
        set(slippage_df.columns)
    ), f"Slippage validation Failed with columns: {set(slippage_df.columns)}"
    assert REWARD_TARGET_COLUMNS.issubset(
        set(reward_target_df.columns)
    ), f"Reward Target validation Failed with columns: {set(reward_target_df.columns)}"
    assert SERVICE_FEE_COLUMNS.issubset(
        set(service_fee_df.columns)
    ), f"Service Fee validation Failed with columns: {set(service_fee_df.columns)}"


def normalize_address_field(frame: DataFrame, column_name: str) -> None:
    """Lower-cases column_name field"""
    frame[column_name] = frame[column_name].str.lower()


def construct_payout_dataframe(
    payment_df: DataFrame,
    slippage_df: DataFrame,
    reward_target_df: DataFrame,
    service_fee_df: DataFrame,
    config: AccountingConfig,
) -> DataFrame:
    """
    Method responsible for joining datasets related to payouts.
    Namely, reward targets and slippage (coming from Dune)
    with reward and execution data coming from orderbook.
    """
    # 1. Assert existence of required columns.
    validate_df_columns(payment_df, slippage_df, reward_target_df, service_fee_df)

    # 2. Normalize Join Column (and Ethereum Address Field)
    join_column = "solver"
    normalize_address_field(payment_df, join_column)
    normalize_address_field(slippage_df, join_column)
    normalize_address_field(reward_target_df, join_column)
    normalize_address_field(service_fee_df, join_column)

    # 3. Merge the three dataframes (joining on solver)
    merged_df = (
        payment_df.merge(slippage_df, on=join_column, how="left")
        .merge(reward_target_df, on=join_column, how="left")
        .merge(service_fee_df, on=join_column, how="left")
    )

    # 4. Add slippage from fees to slippage
    merged_df["eth_slippage_wei"] = (
        merged_df["eth_slippage_wei"].fillna(0) + merged_df["network_fee_eth"]
    )

    # 5. Compute buffer accounting target
    merged_df["buffer_accounting_target"] = np.where(
        merged_df["pool_address"] != config.reward_config.cow_bonding_pool.address,
        merged_df["solver"],
        merged_df["reward_target"],
    )

    # 6. Add reward token address
    merged_df["reward_token_address"] = (
        config.reward_config.reward_token_address.address
    )

    merged_df["service_fee"] = merged_df["service_fee"].fillna(Fraction(0, 1))  # type: ignore

    return merged_df


def construct_partner_fee_payments(
    partner_fees_df: DataFrame, config: AccountingConfig
) -> tuple[dict[str, int], int]:
    """Compute actual partner fee payments taking partner fee tax into account
    The result is a tuple. The first entry is a dictionary that contains the destination address of
    a partner as a key, and the value is the amount in wei to be transferred to that address, stored
    as an int. The second entry is the total amount of partner fees charged.
    """

    partner_fees_wei: dict[str, int] = {}
    for _, row in partner_fees_df.iterrows():
        if row["partner_list"] is None:
            continue

        # We assume the two lists used below, i.e.,
        # partner_list and partner_fee_eth,
        # are "aligned".

        for i in range(len(row["partner_list"])):
            address = row["partner_list"][i]
            if address in partner_fees_wei:
                partner_fees_wei[address] += int(row["partner_fee_eth"][i])
            else:
                partner_fees_wei[address] = int(row["partner_fee_eth"][i])
    total_partner_fee_wei_untaxed = 0
    total_partner_fee_wei_taxed = 0
    for address, value in partner_fees_wei.items():
        total_partner_fee_wei_untaxed += value
        if address == config.protocol_fee_config.reduced_cut_address:
            reduction_factor = 1 - config.protocol_fee_config.partner_fee_reduced_cut
            partner_fees_wei[address] = int(reduction_factor * value)
            total_partner_fee_wei_taxed += int(reduction_factor * value)
        else:
            reduction_factor = 1 - config.protocol_fee_config.partner_fee_cut
            partner_fees_wei[address] = int(reduction_factor * value)
            total_partner_fee_wei_taxed += int(reduction_factor * value)

    return partner_fees_wei, total_partner_fee_wei_untaxed


def construct_payouts(
    orderbook: MultiInstanceDBFetcher,
    dune: DuneFetcher,
    ignore_slippage_flag: bool,
    config: AccountingConfig,
) -> list[Transfer]:
    """Workflow of solver reward payout logic post-CIP27"""
    # pylint: disable-msg=too-many-locals

    quote_rewards_df = orderbook.get_quote_rewards(dune.start_block, dune.end_block)
    batch_rewards_df = orderbook.get_solver_rewards(
        dune.start_block,
        dune.end_block,
        config.reward_config.batch_reward_cap_upper,
        config.reward_config.batch_reward_cap_lower,
    )
    partner_fees_df = batch_rewards_df[["partner_list", "partner_fee_eth"]]
    batch_rewards_df = batch_rewards_df.drop(
        ["partner_list", "partner_fee_eth"], axis=1
    )

    assert batch_rewards_df["solver"].is_unique, "solver not unique in batch rewards"
    assert quote_rewards_df["solver"].is_unique, "solver not unique in quote rewards"
    merged_df = pandas.merge(
        quote_rewards_df, batch_rewards_df, on="solver", how="outer"
    ).fillna(0)

    service_fee_df = pandas.DataFrame(dune.get_service_fee_status())
    service_fee_df["service_fee"] = [
        service_fee_flag * config.reward_config.service_fee_factor
        for service_fee_flag in service_fee_df["service_fee"]
    ]

    reward_target_df = pandas.DataFrame(dune.get_vouches())
    # construct slippage df
    if ignore_slippage_flag or (not config.buffer_accounting_config.include_slippage):
        slippage_df_temp = pandas.merge(
            merged_df[["solver"]],
            reward_target_df[["solver", "solver_name"]],
            on="solver",
            how="inner",
        )
        slippage_df = slippage_df_temp.assign(
            eth_slippage_wei=[0] * slippage_df_temp.shape[0]
        )
    else:
        slippage_df = pandas.DataFrame(dune.get_period_slippage())
        # TODO - After CIP-20 phased in, adapt query to return `solver` like all the others
        slippage_df = slippage_df.rename(columns={"solver_address": "solver"})

    reward_token = config.reward_config.reward_token_address
    native_token = Address(config.payment_config.wrapped_native_token_address)
    price_day = dune.period.end - timedelta(days=1)
    exchange_rate_native_to_cow = exchange_rate_atoms(
        native_token, reward_token, price_day
    )
    log.info(
        f"An exchange rate of {exchange_rate_native_to_cow:.4f} COW/native token is used."
    )
    converter = TokenConversion(
        eth_to_token=lambda t: exchange_rate_native_to_cow * t,
    )

    complete_payout_df = construct_payout_dataframe(
        # Fetch and extend auction data from orderbook.
        payment_df=extend_payment_df(
            pdf=merged_df,
            # provide token conversion functions (ETH <--> COW)
            converter=converter,
            config=config,
        ),
        # Dune: Fetch Solver Slippage & Reward Targets
        slippage_df=slippage_df,
        reward_target_df=reward_target_df,
        service_fee_df=service_fee_df,
        config=config,
    )
    # Sort by solver before breaking this data frame into Transfer objects.
    complete_payout_df = complete_payout_df.sort_values("solver")

    # compute partner fees
    partner_fees_wei, total_partner_fee_wei_untaxed = construct_partner_fee_payments(
        partner_fees_df, config
    )
    raw_protocol_fee_wei = int(complete_payout_df.protocol_fee_eth.sum())
    final_protocol_fee_wei = raw_protocol_fee_wei - total_partner_fee_wei_untaxed
    total_partner_fee_wei_taxed = sum(partner_fees_wei.values())
    partner_fee_tax_wei = total_partner_fee_wei_untaxed - total_partner_fee_wei_taxed

    performance_reward = complete_payout_df["primary_reward_cow"].sum()
    quote_reward = complete_payout_df["quote_reward_cow"].sum()

    service_fee = sum(
        RewardAndPenaltyDatum.from_series(payment).total_service_fee()
        for _, payment in complete_payout_df.iterrows()
    )

    log_saver.print(
        "Payment breakdown (ignoring service fees):\n"
        f"Performance Reward: {performance_reward / 10 ** 18:.4f}\n"
        f"Quote Reward: {quote_reward / 10 ** 18:.4f}\n"
        f"Protocol Fees: {final_protocol_fee_wei / 10 ** 18:.4f}\n"
        f"Partner Fees Tax: {partner_fee_tax_wei / 10 ** 18:.4f}\n"
        f"Partner Fees: {total_partner_fee_wei_taxed / 10 ** 18:.4f}\n"
        f"COW DAO Service Fees: {service_fee / 10 ** 18:.4f}\n",
        category=Category.TOTALS,
    )
    payouts = prepare_transfers(
        complete_payout_df,
        dune.period,
        final_protocol_fee_wei,
        partner_fee_tax_wei,
        partner_fees_wei,
        config,
    )
    for overdraft in payouts.overdrafts:
        log_saver.print(str(overdraft), Category.OVERDRAFT)
    return payouts.transfers
