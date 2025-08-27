from fractions import Fraction

import pytest
import pandas
from pandas import DataFrame

from src.config import Network, RewardConfig
from src.fetch.rewards import (
    compute_rewards,
    REWARDS_COLUMNS,
)


def test_compute_rewards():
    """Test rewards computation"""
    batch_data = DataFrame(
        {
            "solver": ["solver_1", "solver_2"],
            "primary_reward_eth": [10**15, 10**16],
        }
    )
    quote_rewards = DataFrame(
        {"solver": ["solver_2", "solver_3"], "num_quotes": [10, 100]}
    )
    exchange_rate = Fraction(1000, 1)
    reward_config = RewardConfig.from_network(Network.MAINNET)

    rewards = compute_rewards(
        batch_data,
        quote_rewards,
        exchange_rate,
        reward_config,
    )

    reward_per_quote = 7 * 10**17  # capped via ETH
    expected_rewards = DataFrame(
        {
            "solver": ["solver_1", "solver_2", "solver_3"],
            "primary_reward_eth": [10**15, 10**16, 0],
            "primary_reward_cow": [
                int(exchange_rate * 10**15),
                int(exchange_rate * 10**16),
                0,
            ],
            "quote_reward_cow": [0, reward_per_quote * 10, reward_per_quote * 100],
            "reward_token_address": [
                str(reward_config.reward_token_address),
                str(reward_config.reward_token_address),
                str(reward_config.reward_token_address),
            ],
        }
    ).astype(object)

    pandas.testing.assert_frame_equal(rewards, expected_rewards)


def test_compute_rewards_empty():
    """Test that code also works for empty data."""
    batch_data = DataFrame(
        {
            "solver": [],
            "primary_reward_eth": [],
        }
    )
    quote_rewards = DataFrame({"solver": [], "num_quotes": []})
    exchange_rate = Fraction(1000, 1)
    reward_config = RewardConfig.from_network(Network.MAINNET)

    rewards = compute_rewards(
        batch_data,
        quote_rewards,
        exchange_rate,
        reward_config,
    )
    expected_rewards = DataFrame({column: [] for column in REWARDS_COLUMNS}).astype(
        object
    )

    pandas.testing.assert_frame_equal(rewards, expected_rewards)


def test_compute_rewards_wrong_columns():
    """Test column validation"""
    legit_batch_data = DataFrame(
        {
            "solver": [],
            "primary_reward_eth": [],
        }
    )
    legit_quote_rewards = DataFrame({"solver": [], "num_quotes": []})
    exchange_rate = Fraction(1000, 1)
    reward_config = RewardConfig.from_network(Network.MAINNET)

    wrong_columns = DataFrame({"wrong_column": []})

    with pytest.raises(AssertionError):
        compute_rewards(
            wrong_columns,
            legit_quote_rewards,
            exchange_rate,
            reward_config,
        )

    with pytest.raises(AssertionError):
        compute_rewards(
            legit_batch_data,
            wrong_columns,
            exchange_rate,
            reward_config,
        )
