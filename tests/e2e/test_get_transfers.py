import unittest
import pandas as pd
from duneapi.api import DuneAPI

from src.fetch.transfer_file import (
    get_cow_rewards,
    get_eth_spent,
    dashboard_url,
    map_reward,
)
from src.models import AccountingPeriod


def reward_for_tx(
    df: pd.DataFrame, tx_hash: str, risk_free: bool, jit_batch: bool
) -> tuple[int, float]:
    batch_subset = df.loc[df["tx_hash"] == tx_hash]
    order_rewards = batch_subset[["amount"]].apply(
        lambda x: map_reward(x.amount, risk_free, jit_batch),
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


if __name__ == "__main__":
    unittest.main()
