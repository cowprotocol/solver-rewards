import unittest
import pandas as pd
from duneapi.api import DuneAPI

from src.fetch.orderbook_rewards import get_orderbook_rewards
from src.fetch.risk_free_batches import get_risk_free_batches
from src.fetch.transfer_file import (
    map_reward,
    unsafe_batches,
)
from src.models import AccountingPeriod


def reward_for_tx(
    df: pd.DataFrame, tx_hash: str, risk_free: bool, jit_batch: bool
) -> tuple[int, float]:
    print(df, tx_hash, risk_free, jit_batch)
    batch_subset = df.loc[df["tx_hash"] == tx_hash]
    order_rewards = batch_subset[["amount"]].apply(
        lambda x: map_reward(x.amount, risk_free, jit_batch),
        axis=1,
    )
    return order_rewards.size, order_rewards.sum()


class TestPerBatchRewards(unittest.TestCase):
    """
    These tests aren't actually necessary because their logic is captured by a unit test
    tests/unit/test_reward_aggregation.py
    cf: https://github.com/cowprotocol/solver-rewards/pull/107#issuecomment-1288566854
    """

    def setUp(self) -> None:
        dune = DuneAPI.new_from_environment()
        period = AccountingPeriod("2022-10-18")
        start_block, end_block = period.get_block_interval(dune)

        self.rewards_df = get_orderbook_rewards(start_block, end_block)
        self.risk_free_batches = get_risk_free_batches(dune, period)
        self.jit_batches = unsafe_batches(self.rewards_df)

    def test_buffer_trade(self):
        tx_hash = "0x6b6181e95ae837376dd15adbe7801bffffee639dbc8f18b918ace9645a5c1be2"
        self.assertEqual(
            reward_for_tx(
                self.rewards_df,
                tx_hash,
                tx_hash in self.risk_free_batches,
                tx_hash in self.jit_batches,
            ),
            (1, 37.0),
        )

    def test_perfect_cow_with_native_liquidity(self):
        tx_hash = "0x72e4c54e9c9dc2ee2a09dd242bf80abc39d122af0813ff4d570d3ce04eea8468"
        self.assertEqual(
            reward_for_tx(
                self.rewards_df,
                tx_hash,
                tx_hash in self.risk_free_batches,
                tx_hash in self.jit_batches,
            ),
            (2, 37.0),
        )

    def test_perfect_cow_with_foreign_liquidity(self):
        tx_hash = "0x43bfe76d590966c7539f1ea0bb7989edc1289f989eaf8d84589c3508c5066c2c"
        self.assertEqual(
            reward_for_tx(
                self.rewards_df,
                tx_hash,
                tx_hash in self.risk_free_batches,
                tx_hash in self.jit_batches,
            ),
            (2, 39.51661869443983),
        )


if __name__ == "__main__":
    unittest.main()
