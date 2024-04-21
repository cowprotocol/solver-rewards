import unittest

import pandas
from dune_client.types import Address
from pandas import DataFrame

from src.constants import COW_TOKEN_ADDRESS
from src.fetch.payouts import (
    extend_payment_df,
    normalize_address_field,
    validate_df_columns,
    construct_payout_dataframe,
    TokenConversion,
    prepare_transfers,
    RewardAndPenaltyDatum,
    QUOTE_REWARD_COW,
    PROTOCOL_FEE_SAFE,
)
from src.models.accounting_period import AccountingPeriod
from src.models.overdraft import Overdraft
from src.models.token import Token
from src.models.transfer import Transfer


class TestPayoutTransformations(unittest.TestCase):
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
        self.num_quotes = [0, 0, 10, 20]
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

        self.primary_reward_eth = [
            600000000000000.00000,
            12000000000000000.00000,
            -10000000000000000.00000,
            0.00000,
        ]
        self.batch_participation = [
            7,
            2,
            7,
            6,
        ]
        self.protocol_fee_eth = [
            1000000000000000.0,
            2000000000000000.0,
            0.0,
            0.0,
        ]
        self.network_fee_eth = [
            2000000000000000.0,
            4000000000000000.0,
            0.0,
            0.0,
        ]
        # Mocking TokenConversion!
        self.mock_converter = TokenConversion(
            eth_to_token=lambda t: int(t * 1000), token_to_eth=lambda t: t // 1000
        )

    def test_extend_payment_df(self):
        base_data_dict = {
            "solver": self.solvers,
            "num_quotes": self.num_quotes,
            "primary_reward_eth": self.primary_reward_eth,
            "num_participating_batches": self.batch_participation,
            "protocol_fee_eth": self.protocol_fee_eth,
            "network_fee_eth": self.network_fee_eth,
        }
        base_payout_df = DataFrame(base_data_dict)
        result = extend_payment_df(base_payout_df, converter=self.mock_converter)
        expected_data_dict = {
            "solver": self.solvers,
            "num_quotes": self.num_quotes,
            "primary_reward_eth": [
                600000000000000.00000,
                12000000000000000.00000,
                -10000000000000000.00000,
                0.00000,
            ],
            "num_participating_batches": self.batch_participation,
            "protocol_fee_eth": self.protocol_fee_eth,
            "network_fee_eth": self.network_fee_eth,
            "primary_reward_cow": [
                600000000000000000.0,
                12000000000000000000.0,
                -10000000000000000000.0,
                0.0,
            ],
            "secondary_reward_cow": [
                1909090909090909000000.00000,
                545454545454545440000.00000,
                1909090909090909000000.00000,
                1636363636363636200000.00000,
            ],
            "secondary_reward_eth": [
                1909090909090909000.00000,
                545454545454545440.00000,
                1909090909090909000.00000,
                1636363636363636200.00000,
            ],
            "quote_reward_cow": [
                0.00000,
                0.00000,
                6000000000000000000.00000,
                12000000000000000000.00000,
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
                "num_participating_batches": [],
                "protocol_fee_eth": [],
                "network_fee_eth": [],
                "primary_reward_eth": [],
                "primary_reward_cow": [],
                "secondary_reward_cow": [],
                "secondary_reward_eth": [],
                "quote_reward_cow": [],
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
                    "num_quotes": self.num_quotes,
                    "primary_reward_eth": self.primary_reward_eth,
                    "num_participating_batches": self.batch_participation,
                    "protocol_fee_eth": self.protocol_fee_eth,
                    "network_fee_eth": self.network_fee_eth,
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
                "solver": self.solvers,
                "num_quotes": self.num_quotes,
                "primary_reward_eth": [600000000000000.0, 1.2e16, -1e16, 0.0],
                "num_participating_batches": [7, 2, 7, 6],
                "protocol_fee_eth": [
                    1000000000000000.0,
                    2000000000000000.0,
                    0.0,
                    0.0,
                ],
                "network_fee_eth": [
                    2000000000000000.0,
                    4000000000000000.0,
                    0.0,
                    0.0,
                ],
                "primary_reward_cow": [
                    600000000000000000.0,
                    12000000000000000000.0,
                    -10000000000000000000.0,
                    0.0,
                ],
                "secondary_reward_cow": [
                    1909090909090909000000.00000,
                    545454545454545440000.00000,
                    1909090909090909000000.00000,
                    1636363636363636200000.00000,
                ],
                "secondary_reward_eth": [
                    1909090909090909000.00000,
                    545454545454545440.00000,
                    1909090909090909000.00000,
                    1636363636363636200.00000,
                ],
                "quote_reward_cow": [
                    0.00000,
                    0.00000,
                    6000000000000000000.00000,
                    12000000000000000000.00000,
                ],
                "solver_name": ["S_1", "S_2", "S_3", None],
                "eth_slippage_wei": [2000000000000001.0, 4000000000000000.0, -1.0, 0.0],
                "reward_target": [
                    "0x0000000000000000000000000000000000000005",
                    "0x0000000000000000000000000000000000000006",
                    "0x0000000000000000000000000000000000000007",
                    "0x0000000000000000000000000000000000000008",
                ],
            }
        )

        self.assertIsNone(pandas.testing.assert_frame_equal(expected, result))

    def test_prepare_transfers(self):
        # Need Example of every possible scenario
        full_payout_data = DataFrame(
            {
                "solver": self.solvers,
                "num_quotes": self.num_quotes,
                "primary_reward_eth": [600000000000000.0, 1.2e16, -1e16, 0.0],
                "protocol_fee_eth": self.protocol_fee_eth,
                "network_fee_eth": [100.0, 200.0, 300.0, 0.0],
                "primary_reward_cow": [
                    600000000000000000.0,
                    12000000000000000000.0,
                    -10000000000000000000.0,
                    0.0,
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
                "quote_reward_cow": [
                    0.00000,
                    0.00000,
                    90000000000000000000.00000,
                    180000000000000000000.00000,
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
        period = AccountingPeriod("1985-03-10", 1)
        protocol_fee_amount = sum(self.protocol_fee_eth)
        payout_transfers = prepare_transfers(
            full_payout_data, period, protocol_fee_amount, 0, {}
        )
        self.assertEqual(
            [
                Transfer(
                    token=None,
                    recipient=Address(self.solvers[0]),
                    amount_wei=1,
                ),
                Transfer(
                    token=Token(COW_TOKEN_ADDRESS),
                    recipient=Address(self.reward_targets[0]),
                    amount_wei=663636363636363640,
                ),
                Transfer(
                    token=Token(COW_TOKEN_ADDRESS),
                    recipient=Address(self.reward_targets[1]),
                    amount_wei=12018181818181818180,
                ),
                Transfer(
                    token=Token(COW_TOKEN_ADDRESS),
                    recipient=Address(self.reward_targets[2]),
                    amount_wei=90000000000000000000,
                ),
                Transfer(
                    token=Token(COW_TOKEN_ADDRESS),
                    recipient=Address(self.reward_targets[3]),
                    amount_wei=180000000000000000000,
                ),
                Transfer(
                    token=Token(COW_TOKEN_ADDRESS),
                    recipient=Address(self.reward_targets[3]),
                    amount_wei=54545454545454544,
                ),
                Transfer(
                    token=None,
                    recipient=PROTOCOL_FEE_SAFE,
                    amount_wei=3000000000000000,
                ),
            ],
            payout_transfers.transfers,
        )

        self.assertEqual(
            payout_transfers.overdrafts,
            [
                Overdraft(
                    period,
                    account=Address(self.solvers[2]),
                    wei=9936363636363638,
                    name="S_3",
                )
            ],
        )


class TestRewardAndPenaltyDatum(unittest.TestCase):
    def setUp(self) -> None:
        self.solver = Address.from_int(1)
        self.solver_name = "Solver1"
        self.reward_target = Address.from_int(2)
        self.cow_token = Token(COW_TOKEN_ADDRESS)
        self.conversion_rate = 1000

    def sample_record(
        self,
        primary_reward: int,
        secondary_reward: int,
        slippage: int,
        num_quotes: int,
    ):
        """Assumes a conversion rate of ETH:COW <> 1:self.conversion_rate"""
        return RewardAndPenaltyDatum(
            solver=self.solver,
            solver_name=self.solver_name,
            reward_target=self.reward_target,
            primary_reward_eth=primary_reward,
            primary_reward_cow=primary_reward * self.conversion_rate,
            secondary_reward_eth=secondary_reward,
            secondary_reward_cow=secondary_reward * self.conversion_rate,
            slippage_eth=slippage,
            quote_reward_cow=QUOTE_REWARD_COW * num_quotes,
        )

    def test_invalid_input(self):
        """Test that negative and secondary and quote rewards throw an error."""

        # invalid secondary reward
        with self.assertRaises(AssertionError):
            self.sample_record(0, -1, 0, 0)

        # invalid quote reward
        with self.assertRaises(AssertionError):
            self.sample_record(0, 0, 0, -1)

    def test_reward_datum_0_0_0_0(self):
        """Without data there is no payout and no overdraft."""
        test_datum = self.sample_record(0, 0, 0, 0)
        self.assertFalse(test_datum.is_overdraft())
        self.assertEqual(test_datum.as_payouts(), [])

    def test_reward_datum_pm1_0_0_0(self):
        """Primary reward only."""

        # positive reward is paid in COW
        primary_reward = 1
        test_datum = self.sample_record(primary_reward, 0, 0, 0)
        self.assertFalse(test_datum.is_overdraft())
        self.assertEqual(
            test_datum.as_payouts(),
            [
                Transfer(
                    token=self.cow_token,
                    recipient=self.reward_target,
                    amount_wei=primary_reward * self.conversion_rate,
                )
            ],
        )

        # negative reward gives overdraft
        primary_reward = -1
        test_datum = self.sample_record(primary_reward, 0, 0, 0)
        self.assertTrue(test_datum.is_overdraft())
        self.assertEqual(test_datum.as_payouts(), [])

    def test_reward_datum_0_0_pm1_0(self):
        """Slippag only."""

        # positive slippage is paid in ETH
        slippage = 1
        test_datum = self.sample_record(0, 0, slippage, 0)
        self.assertFalse(test_datum.is_overdraft())
        self.assertEqual(
            test_datum.as_payouts(),
            [Transfer(token=None, recipient=self.solver, amount_wei=slippage)],
        )

        # negative slippage gives overdraft
        slippage = -1
        test_datum = self.sample_record(0, 0, slippage, 0)
        self.assertTrue(test_datum.is_overdraft())
        self.assertEqual(test_datum.as_payouts(), [])

    def test_reward_datum_0_0_0_1(self):
        """Quote rewards only."""
        num_quotes = 1
        test_datum = self.sample_record(0, 0, 0, num_quotes)
        self.assertFalse(test_datum.is_overdraft())
        self.assertEqual(
            test_datum.as_payouts(),
            [
                Transfer(
                    token=self.cow_token,
                    recipient=self.reward_target,
                    amount_wei=6000000000000000000 * num_quotes,
                )
            ],
        )

    def test_reward_datum_4_2_1_0(self):
        """COW payment for rewards, ETH payment for slippage."""
        primary_reward, secondary_reward, slippage, num_quotes = 4, 2, 1, 0
        test_datum = self.sample_record(primary_reward, secondary_reward, slippage, 0)
        self.assertFalse(test_datum.is_overdraft())
        self.assertEqual(
            test_datum.as_payouts(),
            [
                Transfer(
                    token=None,
                    recipient=self.solver,
                    amount_wei=slippage,
                ),
                Transfer(
                    token=self.cow_token,
                    recipient=self.reward_target,
                    amount_wei=(primary_reward + secondary_reward)
                    * self.conversion_rate,
                ),
            ],
        )

    def test_reward_datum_slippage_reduces_reward(self):
        """Negative slippage reduces COW reward."""
        primary_reward, secondary_reward, slippage, num_quotes = 4, 2, -1, 0
        test_datum = self.sample_record(primary_reward, secondary_reward, slippage, 0)
        self.assertFalse(test_datum.is_overdraft())
        self.assertEqual(
            test_datum.as_payouts(),
            [
                Transfer(
                    token=self.cow_token,
                    recipient=self.reward_target,
                    amount_wei=(primary_reward + secondary_reward + slippage)
                    * self.conversion_rate,
                ),
            ],
        )

    def test_reward_datum_slippage_exceeds_reward(self):
        """Negative slippage leads to overtraft."""
        primary_reward, participation, slippage = 1, 2, -4
        test_datum = self.sample_record(primary_reward, participation, slippage, 0)
        self.assertTrue(test_datum.is_overdraft())
        self.assertEqual(test_datum.as_payouts(), [])

    def test_reward_datum_reward_reduces_slippage(self):
        """Negative reward  reduces ETH slippage payment."""
        primary_reward, secondary_reward, slippage = -2, 1, 3
        test_datum = self.sample_record(primary_reward, secondary_reward, slippage, 0)
        self.assertEqual(
            test_datum.total_outgoing_eth(),
            primary_reward + secondary_reward + slippage,
        )
        self.assertEqual(
            test_datum.as_payouts(),
            [
                Transfer(
                    token=None,
                    recipient=self.solver,
                    amount_wei=test_datum.total_outgoing_eth(),
                ),
            ],
        )


if __name__ == "__main__":
    unittest.main()
