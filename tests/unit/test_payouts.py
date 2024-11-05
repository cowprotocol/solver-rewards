import unittest
from fractions import Fraction

import pandas
from dune_client.types import Address
from pandas import DataFrame

from src.constants import COW_BONDING_POOL, COW_TOKEN_ADDRESS
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
    SERVICE_FEE_FACTOR,
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
        self.pool_addresses = list(
            map(
                str,
                [
                    COW_BONDING_POOL,
                    Address.from_int(10),
                    Address.from_int(11),
                    Address.from_int(12),
                ],
            )
        )
        self.service_fee = [
            Fraction(0, 100),
            Fraction(0, 100),
            Fraction(0, 100),
            Fraction(15, 100),
        ]

        self.primary_reward_eth = [
            600000000000000.00000,
            12000000000000000.00000,
            -10000000000000000.00000,
            0.00000,
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
        self.mock_converter = TokenConversion(eth_to_token=lambda t: int(t * 1000))

    def test_extend_payment_df(self):
        base_data_dict = {
            "solver": self.solvers,
            "num_quotes": self.num_quotes,
            "primary_reward_eth": self.primary_reward_eth,
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
            "protocol_fee_eth": self.protocol_fee_eth,
            "network_fee_eth": self.network_fee_eth,
            "primary_reward_cow": [
                600000000000000000.0,
                12000000000000000000.0,
                -10000000000000000000.0,
                0.0,
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
                "protocol_fee_eth": [],
                "network_fee_eth": [],
                "primary_reward_eth": [],
                "primary_reward_cow": [],
                "quote_reward_cow": [],
            }
        )
        legit_slippages = DataFrame(
            {"solver": [], "solver_name": [], "eth_slippage_wei": []}
        )
        legit_reward_targets = DataFrame(
            {"solver": [], "reward_target": [], "pool_address": []}
        )
        legit_service_fees = DataFrame({"solver": [], "service_fee": []})

        failing_df = DataFrame({})

        with self.assertRaises(AssertionError):
            validate_df_columns(
                payment_df=legit_payments,
                slippage_df=legit_reward_targets,
                reward_target_df=legit_reward_targets,
                service_fee_df=failing_df,
            )
        with self.assertRaises(AssertionError):
            validate_df_columns(
                payment_df=legit_payments,
                slippage_df=legit_reward_targets,
                reward_target_df=failing_df,
                service_fee_df=legit_service_fees,
            )
        with self.assertRaises(AssertionError):
            validate_df_columns(
                payment_df=legit_payments,
                slippage_df=failing_df,
                reward_target_df=legit_reward_targets,
                service_fee_df=legit_service_fees,
            )
        with self.assertRaises(AssertionError):
            validate_df_columns(
                payment_df=failing_df,
                slippage_df=legit_slippages,
                reward_target_df=legit_reward_targets,
                service_fee_df=legit_service_fees,
            )

        self.assertIsNone(
            validate_df_columns(
                payment_df=legit_payments,
                slippage_df=legit_slippages,
                reward_target_df=legit_reward_targets,
                service_fee_df=legit_service_fees,
            )
        )

    def test_construct_payouts(self):
        payments = extend_payment_df(
            pdf=DataFrame(
                {
                    "solver": self.solvers,
                    "num_quotes": self.num_quotes,
                    "primary_reward_eth": self.primary_reward_eth,
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
            {
                "solver": self.solvers,
                "reward_target": self.reward_targets,
                "pool_address": self.pool_addresses,
            }
        )

        service_fee_df = DataFrame(
            {"solver": self.solvers, "service_fee": self.service_fee}
        )

        result = construct_payout_dataframe(
            payment_df=payments,
            slippage_df=slippages,
            reward_target_df=reward_targets,
            service_fee_df=service_fee_df,
        )
        expected = DataFrame(
            {
                "solver": self.solvers,
                "num_quotes": self.num_quotes,
                "primary_reward_eth": [600000000000000.0, 1.2e16, -1e16, 0.0],
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
                "pool_address": [
                    str(COW_BONDING_POOL),
                    "0x0000000000000000000000000000000000000010",
                    "0x0000000000000000000000000000000000000011",
                    "0x0000000000000000000000000000000000000012",
                ],
                "service_fee": [
                    Fraction(0, 100),
                    Fraction(0, 100),
                    Fraction(0, 100),
                    Fraction(15, 100),
                ],
                "buffer_accounting_target": [
                    str(self.solvers[0]),
                    "0x0000000000000000000000000000000000000006",
                    "0x0000000000000000000000000000000000000007",
                    "0x0000000000000000000000000000000000000008",
                ],
                "reward_token_address": [
                    str(COW_TOKEN_ADDRESS),
                    str(COW_TOKEN_ADDRESS),
                    str(COW_TOKEN_ADDRESS),
                    str(COW_TOKEN_ADDRESS),
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
                "pool_address": [
                    "0x5d4020b9261f01b6f8a45db929704b0ad6f5e9e6",
                    "0x0000000000000000000000000000000000000026",
                    "0x0000000000000000000000000000000000000027",
                    "0x0000000000000000000000000000000000000028",
                ],
                "service_fee": [
                    Fraction(0, 100),
                    Fraction(0, 100),
                    Fraction(0, 100),
                    Fraction(15, 100),
                ],
                "buffer_accounting_target": [
                    self.solvers[0],
                    "0x0000000000000000000000000000000000000006",
                    "0x0000000000000000000000000000000000000007",
                    "0x0000000000000000000000000000000000000008",
                ],
                "reward_token_address": [
                    str(COW_TOKEN_ADDRESS),
                    str(COW_TOKEN_ADDRESS),
                    str(COW_TOKEN_ADDRESS),
                    str(COW_TOKEN_ADDRESS),
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
                    amount_wei=600000000000000000,
                ),
                Transfer(
                    token=Token(COW_TOKEN_ADDRESS),
                    recipient=Address(self.reward_targets[1]),
                    amount_wei=12000000000000000000,
                ),
                Transfer(
                    token=Token(COW_TOKEN_ADDRESS),
                    recipient=Address(self.reward_targets[2]),
                    amount_wei=90000000000000000000,
                ),
                Transfer(
                    token=Token(COW_TOKEN_ADDRESS),
                    recipient=Address(self.reward_targets[3]),
                    amount_wei=int(180000000000000000000 * (1 - SERVICE_FEE_FACTOR)),
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
                    wei=10000000000000001,
                    name="S_3",
                )
            ],
        )


class TestRewardAndPenaltyDatum(unittest.TestCase):
    def setUp(self) -> None:
        self.solver = Address.from_int(1)
        self.solver_name = "Solver1"
        self.reward_target = Address.from_int(2)
        self.buffer_accounting_target = Address.from_int(3)
        self.reward_token_address = COW_TOKEN_ADDRESS
        self.conversion_rate = 1000

    def sample_record(
        self,
        primary_reward: int,
        slippage: int,
        num_quotes: int,
        service_fee: Fraction = Fraction(0, 1),
    ):
        """Assumes a conversion rate of ETH:COW <> 1:self.conversion_rate"""
        return RewardAndPenaltyDatum(
            solver=self.solver,
            solver_name=self.solver_name,
            reward_target=self.reward_target,
            buffer_accounting_target=self.buffer_accounting_target,
            primary_reward_eth=primary_reward,
            primary_reward_cow=primary_reward * self.conversion_rate,
            slippage_eth=slippage,
            quote_reward_cow=QUOTE_REWARD_COW * num_quotes,
            service_fee=service_fee,
            reward_token_address=self.reward_token_address,
        )

    def test_invalid_input(self):
        """Test that negative and quote rewards throw an error."""

        # invalid quote reward
        with self.assertRaises(AssertionError):
            self.sample_record(0, 0, -1)

    def test_reward_datum_0_0_0(self):
        """Without data there is no payout and no overdraft."""
        test_datum = self.sample_record(0, 0, 0)
        self.assertFalse(test_datum.is_overdraft())
        self.assertEqual(test_datum.as_payouts(), [])

    def test_reward_datum_pm1_0_0(self):
        """Primary reward only."""

        # positive reward is paid in COW
        primary_reward = 1
        test_datum = self.sample_record(primary_reward, 0, 0)
        self.assertFalse(test_datum.is_overdraft())
        self.assertEqual(
            test_datum.as_payouts(),
            [
                Transfer(
                    token=Token(self.reward_token_address),
                    recipient=self.reward_target,
                    amount_wei=primary_reward * self.conversion_rate,
                )
            ],
        )

        # negative reward gives overdraft
        primary_reward = -1
        test_datum = self.sample_record(primary_reward, 0, 0)
        self.assertTrue(test_datum.is_overdraft())
        self.assertEqual(test_datum.as_payouts(), [])

    def test_reward_datum_0_pm1_0(self):
        """Slippag only."""

        # positive slippage is paid in ETH
        slippage = 1
        test_datum = self.sample_record(0, slippage, 0)
        self.assertFalse(test_datum.is_overdraft())
        self.assertEqual(
            test_datum.as_payouts(),
            [
                Transfer(
                    token=None,
                    recipient=self.buffer_accounting_target,
                    amount_wei=slippage,
                )
            ],
        )

        # negative slippage gives overdraft
        slippage = -1
        test_datum = self.sample_record(0, slippage, 0)
        self.assertTrue(test_datum.is_overdraft())
        self.assertEqual(test_datum.as_payouts(), [])

    def test_reward_datum_0_0_1(self):
        """Quote rewards only."""
        num_quotes = 1
        test_datum = self.sample_record(0, 0, num_quotes)
        self.assertFalse(test_datum.is_overdraft())
        self.assertEqual(
            test_datum.as_payouts(),
            [
                Transfer(
                    token=Token(self.reward_token_address),
                    recipient=self.reward_target,
                    amount_wei=6000000000000000000 * num_quotes,
                )
            ],
        )

    def test_reward_datum_4_1_0(self):
        """COW payment for rewards, ETH payment for slippage."""
        primary_reward, slippage, num_quotes = 4, 1, 0
        test_datum = self.sample_record(primary_reward, slippage, 0)
        self.assertFalse(test_datum.is_overdraft())
        self.assertEqual(
            test_datum.as_payouts(),
            [
                Transfer(
                    token=None,
                    recipient=self.buffer_accounting_target,
                    amount_wei=slippage,
                ),
                Transfer(
                    token=Token(self.reward_token_address),
                    recipient=self.reward_target,
                    amount_wei=(primary_reward) * self.conversion_rate,
                ),
            ],
        )

    def test_reward_datum_slippage_reduces_reward(self):
        """Negative slippage reduces COW reward."""
        primary_reward, slippage, num_quotes = 4, -1, 0
        test_datum = self.sample_record(primary_reward, slippage, 0)
        self.assertFalse(test_datum.is_overdraft())
        self.assertEqual(
            test_datum.as_payouts(),
            [
                Transfer(
                    token=Token(self.reward_token_address),
                    recipient=self.reward_target,
                    amount_wei=(primary_reward + slippage) * self.conversion_rate,
                ),
            ],
        )

    def test_reward_datum_slippage_exceeds_reward(self):
        """Negative slippage leads to overtraft."""
        primary_reward, slippage = 1, -4
        test_datum = self.sample_record(primary_reward, slippage, 0)
        self.assertTrue(test_datum.is_overdraft())
        self.assertEqual(test_datum.as_payouts(), [])

    def test_reward_datum_reward_reduces_slippage(self):
        """Negative reward  reduces ETH slippage payment."""
        primary_reward, slippage = -2, 3
        test_datum = self.sample_record(primary_reward, slippage, 0)
        self.assertEqual(
            test_datum.total_outgoing_eth(),
            primary_reward + slippage,
        )
        self.assertEqual(
            test_datum.as_payouts(),
            [
                Transfer(
                    token=None,
                    recipient=self.buffer_accounting_target,
                    amount_wei=test_datum.total_outgoing_eth(),
                ),
            ],
        )

    def test_performance_reward_service_fee(self):
        """Sevice fee reduces COW reward."""
        primary_reward, num_quotes, service_fee = 100, 0, Fraction(15, 100)
        test_datum = self.sample_record(
            primary_reward=primary_reward,
            slippage=0,
            num_quotes=num_quotes,
            service_fee=service_fee,
        )
        self.assertFalse(test_datum.is_overdraft())
        self.assertEqual(
            test_datum.as_payouts(),
            [
                Transfer(
                    token=Token(self.reward_token_address),
                    recipient=self.reward_target,
                    amount_wei=int(primary_reward * (1 - SERVICE_FEE_FACTOR))
                    * self.conversion_rate,
                ),
            ],
        )

    def test_quote_reward_service_fee(self):
        """Sevice fee reduces COW reward."""
        primary_reward, num_quotes, service_fee = 0, 100, Fraction(15, 100)
        test_datum = self.sample_record(
            primary_reward=primary_reward,
            slippage=0,
            num_quotes=num_quotes,
            service_fee=service_fee,
        )
        self.assertFalse(test_datum.is_overdraft())
        self.assertEqual(
            test_datum.as_payouts(),
            [
                Transfer(
                    token=Token(self.reward_token_address),
                    recipient=self.reward_target,
                    amount_wei=int(
                        6000000000000000000 * num_quotes * (1 - SERVICE_FEE_FACTOR)
                    ),
                ),
            ],
        )


if __name__ == "__main__":
    unittest.main()
