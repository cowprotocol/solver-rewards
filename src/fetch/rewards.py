"""Functionality for rewards."""

from fractions import Fraction

import pandas as pd
from pandas import DataFrame

from src.config import RewardConfig
from src.logger import set_log

log = set_log(__name__)

BATCH_REWARDS_COLUMNS = ["solver", "primary_reward_eth"]
QUOTE_REWARDS_COLUMNS = ["solver", "num_quotes"]

REWARDS_COLUMNS = [
    "solver",
    "primary_reward_eth",
    "primary_reward_cow",
    "quote_reward_cow",
    "reward_token_address",
]


def compute_rewards(
    batch_data: DataFrame,
    quote_rewards: DataFrame,
    exchange_rate: Fraction,
    reward_config: RewardConfig,
) -> DataFrame:
    """Compute solver rewards"""

    # validate batch rewards and quote rewards columns
    assert set(BATCH_REWARDS_COLUMNS).issubset(set(batch_data.columns))
    assert set(QUOTE_REWARDS_COLUMNS).issubset(set(quote_rewards.columns))

    with pd.option_context(
        "future.no_silent_downcasting", True
    ):  # remove this after Future warning disappears. We do not depend on down-casting,
        # as we will work with object and int explicitly.
        rewards = (
            batch_data[BATCH_REWARDS_COLUMNS]
            .astype(object)
            .merge(
                quote_rewards[QUOTE_REWARDS_COLUMNS].astype(object),
                how="outer",
                on="solver",
                validate="one_to_one",
            )
            .fillna(0)
        ).astype(object)

    rewards["primary_reward_cow"] = (
        (rewards["primary_reward_eth"] * exchange_rate).apply(int).astype(object)
    )

    # Pandas has poor support for large integers, must cast the constant to float here,
    # otherwise the dtype would be inferred as int64 (which overflows).
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
