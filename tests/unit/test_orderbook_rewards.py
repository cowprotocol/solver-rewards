import unittest

from src.models import AccountingPeriod
from src.update.orderbook_rewards import RewardQuery
import pandas as pd


class TestCowRewardsUpsert(unittest.TestCase):
    def setUp(self) -> None:
        self.aggregate_example = pd.DataFrame(
            {"receiver": ["0x1", "0x2"], "amount": [1234, 5678], "num_trades": [46, 2]}
        )
        self.agg_expected = [
            "('0x1', 46, 1234)",
            "('0x2', 2, 5678)",
        ]
        self.per_order_example = pd.DataFrame(
            {
                "solver": ["s1", "s2", "s3"],
                "tx_hash": ["t1", "t2", "t3"],
                "amount": [1234, 5678, 91011],
                "safe_liquidity": [True, False, None],
            }
        )
        # See https://dune.com/queries/1456810 for Null Test Demonstration
        self.per_order_expected = [
            "('s1', 't1', 1234, True)",
            "('s2', 't2', 5678, False)",
            "('s3', 't3', 91011, Null)",
        ]
        print(self.per_order_example)
        print(self.aggregate_example)

    def test_dune_repr(self):
        self.assertEqual(
            self.agg_expected,
            list(
                self.aggregate_example.apply(
                    lambda x: RewardQuery.AGGREGATE.dune_repr(x), axis=1
                )
            ),
        )

        self.assertEqual(
            self.per_order_expected,
            list(
                self.per_order_example.apply(
                    lambda x: RewardQuery.PER_ORDER.dune_repr(x), axis=1
                )
            ),
        )

    def test_rewards_df_to_dune_list(self):
        self.assertEqual(
            RewardQuery.AGGREGATE.to_dune_list(self.aggregate_example),
            ",\n".join(self.agg_expected),
        )

        self.assertEqual(
            RewardQuery.PER_ORDER.to_dune_list(self.per_order_example),
            ",\n".join(self.per_order_expected),
        )

    def test_aggregate_user_generated_view_query(self):
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
        self.assertEqual(
            expected, RewardQuery.AGGREGATE.dune_query(period, self.aggregate_example)
        )

    def test_per_order_user_generated_view_query(self):
        period = AccountingPeriod("1985-03-10")
        # This is hideous I know... Sorry.
        expected = """
        DROP MATERIALIZED VIEW IF EXISTS dune_user_generated.cow_per_order_rewards_1985031019850317 CASCADE;
        CREATE MATERIALIZED VIEW dune_user_generated.cow_per_order_rewards_1985031019850317 (solver, tx_hash, amount, safe_liquidity) AS (
          SELECT *
          FROM (
              VALUES
        ('s1', 't1', 1234, True),
        ('s2', 't2', 5678, False),
        ('s3', 't3', 91011, Null)
            ) as _
        );
        SELECT * FROM dune_user_generated.cow_per_order_rewards_1985031019850317
        """.strip().replace(
            "        ", ""
        )
        print(RewardQuery.PER_ORDER.dune_query(period, self.per_order_example))
        self.assertEqual(
            expected, RewardQuery.PER_ORDER.dune_query(period, self.per_order_example)
        )


if __name__ == "__main__":
    unittest.main()
