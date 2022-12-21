import os
import unittest
import pandas as pd
from dotenv import load_dotenv
from dune_client.client import DuneClient

from src.fetch.cow_rewards import map_reward
from src.fetch.dune import DuneFetcher
from src.models.accounting_period import AccountingPeriod
from src.pg_client import DualEnvDataframe


def reward_for_tx(df: pd.DataFrame, tx_hash: str, risk_free: bool) -> tuple[int, float]:
    print(df, tx_hash, risk_free)
    batch_subset = df.loc[df["tx_hash"] == tx_hash]
    order_rewards = batch_subset[["amount"]].apply(
        lambda x: map_reward(x.amount, risk_free),
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
        load_dotenv()
        dune = DuneFetcher(
            DuneClient(os.environ["DUNE_API_KEY"]),
            AccountingPeriod("2022-10-18"),
        )
        start_block, end_block = dune.get_block_interval()

        self.rewards_df = DualEnvDataframe.get_orderbook_rewards(start_block, end_block)
        self.risk_free_batches = dune.get_risk_free_batches()

    def test_buffer_trade(self):
        tx_hash = "0x6b6181e95ae837376dd15adbe7801bffffee639dbc8f18b918ace9645a5c1be2"
        self.assertEqual(
            reward_for_tx(
                self.rewards_df,
                tx_hash,
                tx_hash in self.risk_free_batches,
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
            ),
            (2, 37.0),
        )


if __name__ == "__main__":
    unittest.main()
