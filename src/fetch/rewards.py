"""Functionality for rewards."""

from fractions import Fraction

import pandas as pd
from pandas import DataFrame

from src.config import RewardConfig
from src.logger import set_log

log = set_log(__name__)

BATCH_DATA_COLUMNS = ["solver", "primary_reward_eth"]
QUOTE_DATA_COLUMNS = ["solver", "num_quotes"]

REWARDS_COLUMNS = [
    "solver",
    "primary_reward_eth",
    "primary_reward_cow",
    "quote_reward_cow",
    "reward_token_address",
]


def compute_rewards(
    batch_data: DataFrame,
    quote_data: DataFrame,
    exchange_rate: Fraction,
    reward_config: RewardConfig,
) -> DataFrame:
    """Compute solver rewards.

    Parameters
    ----------
    batch_data : DataFrame
        Batch rewards data.
        The columns have to contain BATCH_REWARDS_COLUMNS:
        solver : str
            "0x"-prefixed hex representation of the submission address of a solver.
        primary_reward_eth : int
            Reward for settling batches in wei.
    quote_data : DataFrame
        Quote rewards data.
        The columns have to contain BATCH_REWARDS_COLUMNS:
        solver : str
            "0x"-prefixed hex representation of the submission address of a solver.
        num_quotes : int
            Number of wins in the quote competition of executed orders.
    exchange_rate : Fraction
        Exchange rate of ETH to COW.
    reward_config : RewardConfig
        Reward configuration.

    Returns
    -------
    rewards : DataFrame
        Data frame containing rewards per solver.
        The columns are REWARDS_COLUMNS:
        solver : str
            "0x"-prefixed hex representation of the submission address of a solver.
        primary_reward_eth : int
            Reward for settling batches in wei.
        primary_reward_cow : int
            Reward for settling batches in atoms of COW.
        quote_reward_cow : int
            Reward for providing quotes in atoms of COW.
        reward_token_address : str
            "0x"-prefixed hex representation of the reward token contract address.

    Raises
    ------
    AssertionError
        If input dataframes do not contain required columns or if the result does not have correct
        columns.

    Notes
    -----
    All data frames are set to have data type `object`. Otherwise, implicit conversion to int64 can
    lead to overflows.
    """

    # validate batch data and quote data columns
    assert set(BATCH_DATA_COLUMNS).issubset(set(batch_data.columns))
    assert set(QUOTE_DATA_COLUMNS).issubset(set(quote_data.columns))

    with pd.option_context(
        "future.no_silent_downcasting", True
    ):  # remove this after Future warning disappears. We do not depend on down-casting,
        # as we will work with object and int explicitly.
        rewards = (
            batch_data[BATCH_DATA_COLUMNS]
            .astype(object)
            .merge(
                quote_data[QUOTE_DATA_COLUMNS].astype(object),
                how="outer",
                on="solver",
                validate="one_to_one",
            )
            .fillna(0)
        ).astype(object)

    rewards["primary_reward_cow"] = (
        (rewards["primary_reward_eth"] * exchange_rate).apply(int).astype(object)
    )

    reward_per_quote = min(
        reward_config.quote_reward_cow,
        int(reward_config.quote_reward_cap_native * exchange_rate),
    )
    log.info(f"A reward of {reward_per_quote / 10**18:.4f} COW per quote is used.")

    rewards["quote_reward_cow"] = reward_per_quote * rewards["num_quotes"].apply(
        int
    ).astype(object)
    rewards = rewards.drop("num_quotes", axis=1)

    rewards["reward_token_address"] = str(reward_config.reward_token_address)

    # change all types to object to use native python types
    rewards = rewards.astype(object)

    assert set(rewards.columns) == set(REWARDS_COLUMNS)

    return rewards
