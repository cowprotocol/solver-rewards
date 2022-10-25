import unittest

from src.models import AccountingPeriod
from src.update.orderbook_rewards import (
    dune_repr,
    rewards_df_to_dune_list,
    orderbook_rewards_query,
)
import pandas as pd


class TestCowRewardsUpsert(unittest.TestCase):
    def setUp(self) -> None:
        self.example = pd.DataFrame(
            {"receiver": ["0x1", "0x2"], "amount": [1234, 5678], "num_trades": [46, 2]}
        )
        self.expected = [
            "('0x1', 46, 1234)",
            "('0x2', 2, 5678)",
        ]

    def test_dune_repr(self):
        for i, (_, row) in enumerate(self.example.iterrows()):
            self.assertEqual(self.expected[i], dune_repr(row))

    def test_rewards_df_to_dune_list(self):
        self.assertEqual(
            rewards_df_to_dune_list(self.example), ",\n".join(self.expected)
        )

    def test_rewards_user_generated_view_query(self):
        period = AccountingPeriod("1985-03-10")
        # This is hideous I know... Sorry.
        expected = """
        DROP MATERIALIZED VIEW IF EXISTS dune_user_generated.cow_rewards_1985031019850317 CASCADE;
        CREATE MATERIALIZED VIEW dune_user_generated.cow_rewards_1985031019850317 (solver, num_trades, cow_reward) AS (
          SELECT *
          FROM (
              VALUES
        ('0x1', 46, 1234),
        ('0x2', 2, 5678)
            ) as _
        );
        SELECT * FROM dune_user_generated.cow_rewards_1985031019850317
        """.strip().replace(
            "        ", ""
        )
        self.assertEqual(expected, orderbook_rewards_query(period, self.example))


if __name__ == "__main__":
    unittest.main()
