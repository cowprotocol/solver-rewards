import unittest

import pandas
from dune_client.types import Address
from pandas import DataFrame

from src.fetch.payouts import (
    extend_payment_df,
    normalize_address_field,
    validate_df_columns,
    construct_payout_dataframe,
    TokenConversion,
    prepare_transfers,
    PeriodPayouts,
)
from src.models.accounting_period import AccountingPeriod


class TestFetchPayouts(unittest.TestCase):
    """Contains tests all stray methods in src/fetch/payouts.py"""

    def setUp(self) -> None:

        self.solvers = list(
            map(
                str,
                [
                    Address.from_int(1),
                    Address.from_int(2),
                    Address.from_int(3),
                    Address.from_int(4),
                ],
            )
        )
        self.reward_targets = list(
            map(
                str,
                [
                    Address.from_int(5),
                    Address.from_int(6),
                    Address.from_int(7),
                    Address.from_int(8),
                ],
            )
        )

        self.eth_payments = [
            600000000000000.00000,
            10450000000000000.00000,
            -10000000000000000.00000,
            0.00000,
        ]
        self.execution_costs = [
            800000000000000.00000,
            450000000000000.00000,
            0.00000,
            0.00000,
        ]
        self.batch_participation = [
            7,
            2,
            7,
            6,
        ]
        # Mocking TokenConversion!
        self.mock_converter = TokenConversion(
            eth_to_token=lambda t: int(t * 1000), token_to_eth=lambda t: t // 1000
        )

    def test_extend_payment_df(self):
        base_data_dict: dict = {
            "solver": self.solvers,
            "payment_eth": self.eth_payments,
            "execution_cost_eth": self.execution_costs,
            "num_participating_batches": self.batch_participation,
        }
        base_payout_df = DataFrame(base_data_dict)

        result = extend_payment_df(base_payout_df, converter=self.mock_converter)
        expected_data_dict = {
            "solver": self.solvers,
            "payment_eth": self.eth_payments,
            "execution_cost_eth": self.execution_costs,
            "num_participating_batches": self.batch_participation,
            "reward_eth": [
                -200000000000000.00000,
                10000000000000000.00000,
                -10000000000000000.00000,
                0.00000,
            ],
            "reward_cow": [
                -200000000000000000,
                10000000000000000000,
                -10000000000000000000,
                0,
            ],
            "secondary_reward_cow": [
                63636363636363640.00000,
                18181818181818180.00000,
                63636363636363640.00000,
                54545454545454544.00000,
            ],
            "secondary_reward_eth": [
                63636363636363.00000,
                18181818181818.00000,
                63636363636363.00000,
                54545454545454.00000,
            ],
        }
        expected = DataFrame(expected_data_dict)
        self.assertEqual(set(result.columns), set(expected.columns))
        self.assertIsNone(pandas.testing.assert_frame_equal(expected, result))

    def test_normalize_address_field(self):
        column = "address"
        value = "AbCd"

        test_df = DataFrame({column: [value]})
        normalize_address_field(test_df, column)
        self.assertIsNone(
            pandas.testing.assert_frame_equal(
                test_df, DataFrame({column: [value.lower()]})
            )
        )

    def test_validate_df_columns(self):
        legit_payments = DataFrame(
            {
                "solver": [],
                "payment_eth": [],
                "execution_cost_eth": [],
                "num_participating_batches": [],
                "reward_eth": [],
                "reward_cow": [],
                "secondary_reward_cow": [],
                "secondary_reward_eth": [],
            }
        )
        legit_slippages = DataFrame(
            {"solver": [], "solver_name": [], "eth_slippage_wei": []}
        )
        legit_reward_targets = DataFrame({"solver": [], "reward_target": []})
        failing_df = DataFrame({})

        with self.assertRaises(AssertionError):
            validate_df_columns(
                payment_df=legit_payments,
                slippage_df=legit_reward_targets,
                reward_target_df=failing_df,
            )
        with self.assertRaises(AssertionError):
            validate_df_columns(
                payment_df=legit_payments,
                slippage_df=failing_df,
                reward_target_df=legit_reward_targets,
            )
        with self.assertRaises(AssertionError):
            validate_df_columns(
                payment_df=failing_df,
                slippage_df=legit_slippages,
                reward_target_df=legit_reward_targets,
            )

        self.assertIsNone(
            validate_df_columns(
                payment_df=legit_payments,
                slippage_df=legit_slippages,
                reward_target_df=legit_reward_targets,
            )
        )

    def test_construct_payouts(self):

        payments = extend_payment_df(
            pdf=DataFrame(
                {
                    "solver": self.solvers,
                    "payment_eth": self.eth_payments,
                    "execution_cost_eth": self.execution_costs,
                    "num_participating_batches": self.batch_participation,
                }
            ),
            converter=self.mock_converter,
        )

        slippages = DataFrame(
            {
                "solver": self.solvers[:3],
                # Note that one of the solvers did not appear,
                # in this list (we are testing the left join)
                "solver_name": ["S_1", "S_2", "S_3"],
                "eth_slippage_wei": [1, 0, -1],
            }
        )

        reward_targets = DataFrame(
            {"solver": self.solvers, "reward_target": self.reward_targets}
        )
        result = construct_payout_dataframe(
            payment_df=payments, slippage_df=slippages, reward_target_df=reward_targets
        )
        expected = DataFrame(
            {
                "solver": [
                    "0x0000000000000000000000000000000000000001",
                    "0x0000000000000000000000000000000000000002",
                    "0x0000000000000000000000000000000000000003",
                    "0x0000000000000000000000000000000000000004",
                ],
                "payment_eth": [600000000000000.0, 1.045e16, -1e16, 0.0],
                "execution_cost_eth": [800000000000000.0, 450000000000000.0, 0.0, 0.0],
                "num_participating_batches": [7, 2, 7, 6],
                "reward_eth": [-200000000000000.0, 1e16, -1e16, 0.0],
                "reward_cow": [
                    -200000000000000000,
                    10000000000000000000,
                    -10000000000000000000,
                    0,
                ],
                "secondary_reward_cow": [
                    6.363636363636364e16,
                    1.818181818181818e16,
                    6.363636363636364e16,
                    5.454545454545454e16,
                ],
                "secondary_reward_eth": [
                    63636363636363.0,
                    18181818181818.0,
                    63636363636363.0,
                    54545454545454.0,
                ],
                "solver_name": ["S_1", "S_2", "S_3", None],
                "eth_slippage_wei": [1.0, 0.0, -1.0, None],
                "reward_target": [
                    "0x0000000000000000000000000000000000000005",
                    "0x0000000000000000000000000000000000000006",
                    "0x0000000000000000000000000000000000000007",
                    "0x0000000000000000000000000000000000000008",
                ],
            }
        )

        self.assertIsNone(pandas.testing.assert_frame_equal(result, expected))

    def test_prepare_transfers(self):
        # TODO - write test here
        # Need Example of every possible scenario
        full_payout_data = DataFrame(
            {
                "solver": [
                    "0x0000000000000000000000000000000000000001",
                    "0x0000000000000000000000000000000000000002",
                    "0x0000000000000000000000000000000000000003",
                    "0x0000000000000000000000000000000000000004",
                ],
                "payment_eth": [600000000000000.0, 1.045e16, -1e16, 0.0],
                "execution_cost_eth": [800000000000000.0, 450000000000000.0, 0.0, 0.0],
                "reward_eth": [-200000000000000.0, 1e16, -1e16, 0.0],
                "reward_cow": [
                    -200000000000000000,
                    10000000000000000000,
                    -10000000000000000000,
                    0,
                ],
                "secondary_reward_cow": [
                    6.363636363636364e16,
                    1.818181818181818e16,
                    6.363636363636364e16,
                    5.454545454545454e16,
                ],
                "secondary_reward_eth": [
                    63636363636363.0,
                    18181818181818.0,
                    63636363636363.0,
                    54545454545454.0,
                ],
                "solver_name": ["S_1", "S_2", "S_3", None],
                "eth_slippage_wei": [1.0, 0.0, -1.0, None],
                "reward_target": [
                    "0x0000000000000000000000000000000000000005",
                    "0x0000000000000000000000000000000000000006",
                    "0x0000000000000000000000000000000000000007",
                    "0x0000000000000000000000000000000000000008",
                ],
            }
        )
        payout_transfers = prepare_transfers(
            full_payout_data, period=AccountingPeriod("1985-03-10", 1)
        )
        self.assertEqual(payout_transfers, PeriodPayouts(overdrafts=[], transfers=[]))


if __name__ == "__main__":
    unittest.main()
