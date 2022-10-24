import unittest
import pandas as pd
from duneapi.api import DuneAPI

from src.fetch.orderbook_rewards import get_orderbook_rewards
from src.fetch.risk_free_batches import get_risk_free_batches
from src.fetch.transfer_file import (
    get_cow_rewards,
    get_eth_spent,
    dashboard_url,
    map_reward,
)
from src.models import AccountingPeriod


def reward_for_tx(df: pd.DataFrame, tx_hash: str, risk_free: bool) -> tuple[int, float]:
    batch_subset = df.loc[df["tx_hash"] == tx_hash]
    order_rewards = batch_subset[["amount"]].apply(
        lambda x: map_reward(x.amount, risk_free),
        axis=1,
    )
    return order_rewards.size, order_rewards.sum()


class MyTestCase(unittest.TestCase):
    def setUp(self) -> None:
        self.dune = DuneAPI.new_from_environment()

    def test_get_eth_spent(self):
        eth_transfers = get_eth_spent(self.dune, AccountingPeriod("2022-09-20"))
        self.assertAlmostEqual(
            sum(t.amount_wei for t in eth_transfers),
            16745457506431162000,  # cf: https://dune.com/queries/1323288
            delta=5 * 10**4,  # WEI
        )

    def test_get_cow_rewards(self):
        period = AccountingPeriod("2022-10-18", length_days=2)
        print(f"Check out results at: {dashboard_url(period)}")
        try:
            get_cow_rewards(self.dune, period)
        except AssertionError as err:
            self.fail(f"get_cow_rewards failed with {err}")

    def test_per_order_rewards(self):
        period = AccountingPeriod("2022-10-18")
        start_block, end_block = period.get_block_interval(self.dune)
        rewards_df = get_orderbook_rewards(start_block, end_block)
        risk_free_batches = get_risk_free_batches(self.dune, period)
        # Transactions:
        # 0x6b6181e95ae837376dd15adbe7801bffffee639dbc8f18b918ace9645a5c1be2 -> 37
        # 0x72e4c54e9c9dc2ee2a09dd242bf80abc39d122af0813ff4d570d3ce04eea8468 -> 37
        # 0x82318dd23592f7ccba72fcad43c452c4c426d9e02c7cf3b1f9e7823a0c9a9fc0 -> 74
        # 0x43bfe76d590966c7539f1ea0bb7989edc1289f989eaf8d84589c3508c5066c2c ->
        # https://explorer.cow.fi/tx/0x43bfe76d590966c7539f1ea0bb7989edc1289f989eaf8d84589c3508c5066c2c?tab=orders
        buffer_tx = "0x6b6181e95ae837376dd15adbe7801bffffee639dbc8f18b918ace9645a5c1be2"
        self.assertEqual(
            reward_for_tx(rewards_df, buffer_tx, buffer_tx in risk_free_batches),
            (1, 37.0),
        )

        perfect_cow_native_liquidity = (
            "0x72e4c54e9c9dc2ee2a09dd242bf80abc39d122af0813ff4d570d3ce04eea8468"
        )
        self.assertEqual(
            reward_for_tx(
                rewards_df,
                perfect_cow_native_liquidity,
                perfect_cow_native_liquidity in risk_free_batches,
            ),
            (2, 37.0),
        )

        perfect_cow_foreign_liquidity = (
            "0x43bfe76d590966c7539f1ea0bb7989edc1289f989eaf8d84589c3508c5066c2c"
        )
        self.assertEqual(
            reward_for_tx(
                rewards_df,
                perfect_cow_foreign_liquidity,
                perfect_cow_foreign_liquidity in risk_free_batches,
            ),
            (2, 37.0),
        )


if __name__ == "__main__":
    unittest.main()
