"""Logic for Post CIP 20 Solver Payout Calculation"""
from __future__ import annotations
from dataclasses import dataclass
from datetime import timedelta
from typing import Callable

import pandas
from dune_client.types import Address
from pandas import DataFrame, Series

from src.constants import COW_TOKEN_ADDRESS
from src.fetch.dune import DuneFetcher
from src.fetch.prices import eth_in_token, TokenId, token_in_eth
from src.models.accounting_period import AccountingPeriod
from src.models.overdraft import Overdraft
from src.models.token import Token
from src.models.transfer import Transfer
from src.pg_client import MultiInstanceDBFetcher

PERIOD_BUDGET_COW = 1

PAYMENT_COLUMNS = {
    "solver",
    "payment_eth",
    "execution_cost_eth",
    "secondary_reward_eth",
    "reward_cow",
    "secondary_reward_cow",
}
SLIPPAGE_COLUMNS = {
    "solver",
    "solver_name",
    "eth_slippage_wei",
}
REWARD_TARGET_COLUMNS = {"solver", "reward_target"}

COMPLETE_COLUMNS = PAYMENT_COLUMNS.union(SLIPPAGE_COLUMNS).union(REWARD_TARGET_COLUMNS)


@dataclass
class PeriodPayouts:
    """Dataclass to keep track of reimbursements and rewards"""

    overdrafts: list[Overdraft]
    # ETH Reimbursements & COW Rewards
    transfers: list[Transfer]


@dataclass
class RewardAndPenaltyDatum:  # pylint: disable=too-many-instance-attributes
    """
    Dataclass holding all pertinent information related to a solver's payout (or overdraft)
    """

    solver: Address
    solver_name: str
    reward_target: Address
    exec_cost: int
    payment_eth: int
    secondary_reward_eth: int
    slippage_eth: int
    cow_reward: int
    secondary_reward_cow: int

    @classmethod
    def from_series(cls, frame: Series) -> RewardAndPenaltyDatum:
        """Constructor from row in Dataframe"""
        return cls(
            solver=Address(frame["solver"]),
            solver_name=frame["solver_name"],
            reward_target=Address(frame["reward_target"]),
            exec_cost=int(frame["execution_cost_eth"]),
            payment_eth=int(frame["payment_eth"]),
            slippage_eth=int(frame["eth_slippage_wei"]),
            cow_reward=int(frame["cow_reward"]),
            secondary_reward_eth=int(frame["secondary_reward_eth"]),
            secondary_reward_cow=int(frame["secondary_reward_cow"]),
        )

    def total_outgoing_eth(self) -> int:
        """Total outgoing amount (including slippage) for the payout."""
        return self.payment_eth + self.secondary_reward_eth + self.slippage_eth

    def total_cow_reward(self) -> int:
        """Total outgoing COW token reward"""
        return self.cow_reward + self.secondary_reward_cow

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
        # TODO - decide how to approach the "order of operations" regarding slippage and rewards
        #  Seemingly, the simplest option is to deal with Reward Scheme First and Slippage after.
        #  However, there is this issue with the fact that payment can be negative
        #  (which didn't exist before)
        # We do not handle overdraft scenario here!
        assert not self.is_overdraft()
        if self.total_outgoing_eth() < self.exec_cost:
            # Total outgoing doesn't even cover execution costs,
            # so reimburse as much as possible.
            return [
                Transfer(
                    token=None,
                    recipient=self.solver,
                    amount_wei=int(self.total_outgoing_eth()),
                )
            ]
        # At this point we know that:
        # self.total_outgoing_eth() >= self.exec_cost
        # Now it is time to handle the many cases involving signatures of
        # (payment_eth, secondary_reward_eth, slippage_eth)
        # TODO - THIS IS A MESS!
        #  WAY TOO COMPLICATED TO GET RIGHT IN A SINGLE PR.
        #  The logic of this method must be sorted out separately.

        # primary_eth + secondary_eth and slippage combined all cover execution costs
        # TODO - we have not captured all the cases.
        return [
            Transfer(
                # TODO - this amount could be negative! Will capture this with a test.
                token=None,
                recipient=self.solver,
                amount_wei=int(self.exec_cost + self.slippage_eth),
            ),
            Transfer(
                token=Token(COW_TOKEN_ADDRESS),
                recipient=self.reward_target,
                amount_wei=int(self.total_cow_reward()),
            ),
        ]


@dataclass
class TokenConversion:
    """
    Data Structure containing token conversion methods.
    """

    eth_to_token: Callable
    token_to_eth: Callable


def extend_payment_df(pdf: DataFrame, converter: TokenConversion) -> DataFrame:
    """
    TODO: add type: `eth_to_token` is a function with signature (int -> int)
          add type: `token_to_eth` is a function with signature (int -> int)
                (one is the compositional the inverse of the other)
    Extending the basic columns returned by SQL Query with some after-math:
    - reward_eth as difference of payment and execution_cost
    - reward_cow as conversion from ETH to cow.
    - secondary_reward (as the remaining reward after all has been distributed)
        This is evaluated in both ETH and COW (for different use cases).
    """
    # Note that this can be negative!
    pdf["reward_eth"] = pdf["payment_eth"] - pdf["execution_cost_eth"]
    pdf["reward_cow"] = pdf["reward_eth"].apply(converter.eth_to_token)

    secondary_allocation = max(PERIOD_BUDGET_COW - pdf["reward_cow"].sum(), 0)
    participation_total = pdf["num_participating_batches"].sum()
    pdf["secondary_reward_cow"] = (
        secondary_allocation * pdf["num_participating_batches"] / participation_total
    )
    pdf["secondary_reward_eth"] = pdf["secondary_reward_cow"].apply(
        converter.token_to_eth
    )
    return pdf


def prepare_transfers(payout_df: DataFrame, period: AccountingPeriod) -> PeriodPayouts:
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
            print(f"Solver {payout_datum.solver} owes us! ETH or COW.")
            overdrafts.append(
                Overdraft(
                    period=period,
                    account=payout_datum.solver,
                    name=payout_datum.solver_name,
                    wei=-int(payout_datum.total_outgoing_eth()),
                )
            )
        else:
            # No overdraft, always results in at least one transfer.
            transfers += payout_datum.as_payouts()

    return PeriodPayouts(overdrafts, transfers)


def validate_df_columns(
    payment_df: DataFrame, slippage_df: DataFrame, reward_target_df: DataFrame
) -> None:
    """
    Since we are working with dataframes rather than concrete objects,
    we validate that the expected columns/fields are available within our datasets.
    While it is ok for the input data to contain more columns,
    this method merely validates that the expected ones are there.
    TODO - this might also be a good place to assert types.
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


def normalize_address_field(frame: DataFrame, column_name: str) -> None:
    """Lower-cases column_name field"""
    frame[column_name] = frame[column_name].str.lower()


def construct_payout_dataframe(
    payment_df: DataFrame, slippage_df: DataFrame, reward_target_df: DataFrame
) -> DataFrame:
    """
    Method responsible for joining datasets related to payouts.
    Namely, reward targets and slippage (coming from Dune)
    with reward and execution data coming from orderbook.
    """
    # TODO - After CIP-20 phased in, adapt query to return `solver` like all the others
    slippage_df.rename(columns={"solver_address": "solver"})
    # 1. Assert existence of required columns.
    validate_df_columns(payment_df, slippage_df, reward_target_df)

    # 2. Normalize Join Column (and Ethereum Address Field)
    join_column = "solver"
    normalize_address_field(payment_df, join_column)
    normalize_address_field(slippage_df, join_column)
    normalize_address_field(reward_target_df, join_column)
    # 3. Merge the three dataframes (joining on solver)
    merged_df = payment_df.merge(slippage_df, on=join_column, how="left").merge(
        reward_target_df, on=join_column, how="left"
    )
    merged_df.to_dict()
    return merged_df


def post_cip20_payouts(
    dune: DuneFetcher, orderbook: MultiInstanceDBFetcher
) -> list[Transfer]:
    """Workflow of solver reward payout logic post-CIP20"""
    # Fetch auction data from orderbook.
    # rewards_df = orderbook.get_solver_rewards(dune.start_block, dune.end_block)
    # solver_slippage = pandas.DataFrame(dune.get_period_slippage())
    # reward_targets = dune.get_vouches()

    # Separate values into ETH (execution costs) and COW rewards.
    # payments = split_into_eth_cow(rewards_df, dune.period)
    price_day = dune.period.end - timedelta(days=1)
    reward_token = TokenId.COW

    complete_payout_df = construct_payout_dataframe(
        payment_df=extend_payment_df(
            pdf=orderbook.get_solver_rewards(dune.start_block, dune.end_block),
            converter=TokenConversion(
                eth_to_token=lambda t: eth_in_token(reward_token, t, price_day),
                token_to_eth=lambda t: token_in_eth(reward_token, t, price_day),
            ),
        ),
        slippage_df=pandas.DataFrame(dune.get_period_slippage()),
        reward_target_df=pandas.DataFrame(dune.get_vouches()),
    )
    # TODO - sort by solver first?
    payouts = prepare_transfers(complete_payout_df, dune.period)
    # TODO - make sure to log Overdrafts
    return payouts.transfers
