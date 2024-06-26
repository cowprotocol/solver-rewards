import unittest

import os
import pandas
from pandas import DataFrame

from dune_client.client import DuneClient

from src.models.accounting_period import AccountingPeriod
from src.fetch.dune import DuneFetcher
from src.fetch.payouts import (
    construct_payout_dataframes,
    construct_payouts,
    prepare_transfers,
)
from src.fetch.prices import TokenConversion
from src.pg_client import MultiInstanceDBFetcher


class TestPayouts(unittest.TestCase):
    """Contains tests all stray methods in src/fetch/payouts.py"""

    def setUp(self) -> None:
        self.start_block = "19764411"
        self.end_block = "19814477"
        self.fetcher = MultiInstanceDBFetcher(
            [os.environ["PROD_DB_URL"], os.environ["BARN_DB_URL"]]
        )
        # self.start_block = "19760112"
        # self.end_block = "19760300"
        # self.fetcher = MultiInstanceDBFetcher([os.environ["BARN_DB_URL"]])
        self.dune = DuneFetcher(
            dune=DuneClient(os.environ["DUNE_API_KEY"]),
            period=AccountingPeriod("2024-04-30"),
        )

        # Mocking TokenConversion!
        self.converter = TokenConversion(
            eth_to_token=lambda t: int(t * 1000), token_to_eth=lambda t: t // 1000
        )

    @unittest.skip("Skip this long running test. Run manually to check full ")
    def test_construct_payout_dataframe(self):
        batch_data_df = self.fetcher.get_batch_data(self.start_block, self.end_block)
        trade_data_df = self.fetcher.get_trade_data(self.start_block, self.end_block)
        # slippage is not queried but hardcoded to fixed values
        slippage_df = DataFrame(
            {
                "solver_address": [
                    "0x94aef67903bfe8bf65193a78074c887ba901d043",
                    "0xa697c60706210a5ec6f9ccce364c507e604d9462",
                    "0x01246d541e732d7f15d164331711edff217e4665",
                    "0x849bbdf910465913272a8262dda44279a82c5c76",
                    "0x279fb872beaf64e94890376725c423c0820eda97",
                    "0xaac451d13cf8d6915f859f4c7bc26da2df10eca6",
                ],
                "solver_name": [
                    "0x94aef67903bfe8bf65193a78074c887ba901d043",
                    "0xa697c60706210a5ec6f9ccce364c507e604d9462",
                    "0x01246d541e732d7f15d164331711edff217e4665",
                    "0x849bbdf910465913272a8262dda44279a82c5c76",
                    "0x279fb872beaf64e94890376725c423c0820eda97",
                    "0xaac451d13cf8d6915f859f4c7bc26da2df10eca6",
                ],
                "eth_slippage_wei": [0.0, 0.0, 0.0, 0.0, 0.0, 0.0],
            }
        )
        reward_target_df = pandas.DataFrame(self.dune.get_vouches())
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
                "0x94aef67903bfe8bf65193a78074c887ba901d043",
                "0xa697c60706210a5ec6f9ccce364c507e604d9462",
                "0x01246d541e732d7f15d164331711edff217e4665",
                "0x849bbdf910465913272a8262dda44279a82c5c76",
                "0x279fb872beaf64e94890376725c423c0820eda97",
                "0xaac451d13cf8d6915f859f4c7bc26da2df10eca6",
            ],
            "primary_reward_eth": [
                9.014405e14,
                1.867692e14,
                0,
                0,
                0,
                0,
            ],
            "primary_reward_cow": [
                9.014405e17,
                1.867692e17,
                0.000000e00,
                0.000000e00,
                0.000000e00,
                0.000000e00,
            ],
            "secondary_reward_cow": [
                1.714286e21,
                1.714286e21,
                8.571429e20,
                8.571429e20,
                8.571429e20,
                0.000000e00,
            ],
            "secondary_reward_eth": [
                1.714286e18,
                1.714286e18,
                8.571429e17,
                8.571429e17,
                8.571429e17,
                0.000000e00,
            ],
            "quote_reward_cow": [
                0.000000e00,
                0.000000e00,
                0.000000e00,
                6.000000e17,
                0.000000e00,
                1.200000e18,
            ],
            "solver_name": [
                "0x94aef67903bfe8bf65193a78074c887ba901d043",
                "0xa697c60706210a5ec6f9ccce364c507e604d9462",
                "0x01246d541e732d7f15d164331711edff217e4665",
                "0x849bbdf910465913272a8262dda44279a82c5c76",
                "0x279fb872beaf64e94890376725c423c0820eda97",
                "0xaac451d13cf8d6915f859f4c7bc26da2df10eca6",
            ],  # since slippage querry is skipped
            "slippage_eth": [
                3712178546976961,
                2010368706252343,
                0,
                0,
                0,
                0,
            ],
            "reward_target": [
                "0x2c01b4ad51a67e2d8f02208f54df9ac4c0b778b6",
                "0x6c642cafcbd9d8383250bb25f67ae409147f78b2",
                "0x6c642cafcbd9d8383250bb25f67ae409147f78b2",
                "0x6c642cafcbd9d8383250bb25f67ae409147f78b2",
                "0xa1079e43d086ffbb95e921a4b9bbb2d325dff4ea",
                "0x6c642cafcbd9d8383250bb25f67ae409147f78b2",
            ],
        }

        expected_protocol_partner_fees_dict = {
            "recipient": [
                "0x9FA3c00a92Ec5f96B1Ad2527ab41B3932EFEDa58",
                "0xb64963f95215fde6510657e719bd832bb8bb941b",
                "0xb64963f95215fde6510657e719bd832bb8bb941b",
            ],
            "fee_eth": [
                320650107837438,
                179560288149704,
                56585313147782,
            ],
            "from_partner_fee": [
                True,
                False,
                True,
            ],
            "fee_cow": [
                320650107837438000,
                179560288149704000,
                56585313147782000,
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

    @unittest.skip("Skip this long running test. Run manually to check full ")
    def test_construct_payouts(self):
        """Tests the full creation of transfers starting from an accounting period.
        This tests takes long since it run the Dune slippage query.
        """
        transfers = construct_payouts(self.dune, self.fetcher)

        expected_transfers = []


if __name__ == "__main__":
    unittest.main()
