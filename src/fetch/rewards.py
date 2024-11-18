"""Functionality for rewards."""

from fractions import Fraction

from pandas import DataFrame

from src.config import RewardConfig


BATCH_REWARDS_COLUMNS = ["solver", "primary_reward_eth"]
QUOTE_REWARDS_COLUMNS = ["solver", "num_quotes"]

REWARDS_COLUMNS = [
    "solver",
    "primary_reward_eth",
    "primary_reward_cow",
    "quote_reward_cow",
    "reward_token_address",
]

NUMERICAL_COLUMNS = [
    "primary_reward_eth",
    "primary_reward_cow",
    "quote_reward_cow",
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

    rewards = (
        batch_data[BATCH_REWARDS_COLUMNS]
        .merge(
            quote_rewards[QUOTE_REWARDS_COLUMNS],
            how="outer",
            on="solver",
            validate="one_to_one",
        )
        .fillna(0)
    )

    rewards["primary_reward_cow"] = rewards["primary_reward_eth"] * float(exchange_rate)

    # Pandas has poor support for large integers, must cast the constant to float here,
    # otherwise the dtype would be inferred as int64 (which overflows).
    rewards["quote_reward_cow"] = (
        float(
            min(
                reward_config.quote_reward_cow,
                int(reward_config.quote_reward_cap_native * exchange_rate),
            )
        )
        * rewards["num_quotes"]
    )
    rewards = rewards.drop("num_quotes", axis=1)

    rewards["reward_token_address"] = str(reward_config.reward_token_address)

    # change all types to object to use native python types
    rewards = rewards.astype(object)

    # for number_col in NUMERICAL_COLUMNS:
    #     rewards[number_col] = pandas.to_numeric(rewards[number_col])

    assert set(rewards.columns) == set(REWARDS_COLUMNS)

    return rewards
