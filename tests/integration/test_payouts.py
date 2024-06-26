import unittest

import pandas
from pandas import DataFrame

from src.fetch.payouts import (
    construct_payout_dataframes,
    TokenConversion,
)
from src.pg_client import MultiInstanceDBFetcher


class TestPayoutTransformations(unittest.TestCase):
    """Contains tests all stray methods in src/fetch/payouts.py"""

    def setUp(self) -> None:
        db_url = "postgres:postgres@localhost:5432/postgres"
        self.fetcher = MultiInstanceDBFetcher([db_url])
        with open(
            "./tests/queries/batch_rewards_test_db.sql", "r", encoding="utf-8"
        ) as file:
            self.fetcher.connections[0].execute(file.read())

        # Mocking TokenConversion!
        self.converter = TokenConversion(
            eth_to_token=lambda t: int(t * 1000), token_to_eth=lambda t: t // 1000
        )

    def test_construct_payout_dataframe(self):
        start_block, end_block = "0", "100"
        batch_data_df = self.fetcher.get_batch_data(start_block, end_block)
        trade_data_df = self.fetcher.get_trade_data(start_block, end_block)
        slippage_df = DataFrame(
            {
                "solver_address": ["0x01"],
                "solver_name": ["test_name 1"],
                "eth_slippage_wei": [10**17],
            }
        )
        reward_target_df = DataFrame(
            {"solver": ["0x01"], "pool": ["test_pool"], "reward_target": ["0x0101"]}
        )
        converter = self.converter

        solver_rewards_df, protocol_partner_fees_df = construct_payout_dataframes(
            batch_data_df,
            trade_data_df,
            slippage_df,
            reward_target_df,
            converter,
        )

        expected_solver_rewards_dict = {
            "solver": [
                "0x01",
                "0x02",
                "0x03",
                "0x5111111111111111111111111111111111111111",
                "0x5222222222222222222222222222222222222222",
                "0x5333333333333333333333333333333333333333",
                "0x5444444444444444444444444444444444444444",
            ],
            "primary_reward_eth": [
                2.000000e15,
                3.000000e15,
                3.500000e15,
                5.000000e16,
                1.200000e16,
                -1.000000e16,
                0.000000e00,
            ],
            "primary_reward_cow": [
                2000000000000000000,
                3000000000000000000,
                3500000000000000000,
                50000000000000000000,
                12000000000000000000,
                -10000000000000000000,
                0,
            ],
            "secondary_reward_cow": [
                562500000000000000000,
                562500000000000000000,
                750000000000000000000,
                1312500000000000000000,
                375000000000000000000,
                1312500000000000000000,
                1125000000000000000000,
            ],
            "secondary_reward_eth": [
                5.625000e17,
                5.625000e17,
                7.500000e17,
                1.312500e18,
                3.750000e17,
                1.312500e18,
                1.125000e18,
            ],
            "quote_reward_cow": [
                6.000000e17,
                1.200000e18,
                0.000000e00,
                0.000000e00,
                0.000000e00,
                0.000000e00,
                0.000000e00,
            ],
            "solver_name": ["test_name 1", 0, 0, 0, 0, 0, 0],
            "slippage_eth": [
                1.052875e17,
                3.980198e15,
                1.077918e16,
                0.000000e00,
                0.000000e00,
                0.000000e00,
                0.000000e00,
            ],
            "reward_target": [
                "0x0101",
                None,
                None,
                None,
                None,
                None,
                None,
            ],
        }

        expected_protocol_partner_fees_dict = {
            "recipient": [
                "0xb64963f95215fde6510657e719bd832bb8bb941b",
                "0xb64963f95215fde6510657e719bd832bb8bb941b",
                "0x90a48d5cf7343b08da12e067680b4c6dbfe551be",
            ],
            "fee_eth": [
                3749599479797979,
                32207433450527,
                182508789552988,
            ],
            "from_partner_fee": [
                False,
                True,
                True,
            ],
            "fee_cow": [
                3749599479797979000,
                32207433450527000,
                182508789552988000,
            ],
        }
        expected_solver_rewards = DataFrame(expected_solver_rewards_dict).astype(object)
        expected_protocol_partner_fees = DataFrame(
            expected_protocol_partner_fees_dict
        ).astype(object)

        print("test")
        self.assertEqual(
            set(solver_rewards_df.columns), set(expected_solver_rewards.columns)
        )
        self.assertIsNone(
            pandas.testing.assert_frame_equal(
                solver_rewards_df, expected_solver_rewards
            )
        )

        self.assertEqual(
            set(protocol_partner_fees_df.columns),
            set(expected_protocol_partner_fees.columns),
        )
        self.assertIsNone(
            pandas.testing.assert_frame_equal(
                protocol_partner_fees_df, expected_protocol_partner_fees
            )
        )


if __name__ == "__main__":
    unittest.main()
