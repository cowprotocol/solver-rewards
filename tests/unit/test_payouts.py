import unittest

import pandas
from dune_client.types import Address
from pandas import DataFrame

from src.constants import COW_TOKEN_ADDRESS
from src.fetch.payouts import (
    normalize_address_field,
    RewardAndSlippageDatum,
    ProtocolFeeDatum,
)
from src.fetch.rewards import QUOTE_REWARD_COW

from src.models.token import Token
from src.models.transfer import Transfer


class TestPayouts(unittest.TestCase):
    """Test methods for creation of payouts from reward and fee data"""

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

    def test_invalid_payment_datum(self):
        pass

    def test_prepare_transfers(self):
        pass

    def test_construct_payout_dataframes(self):
        pass

    def test_combine_rewards_and_slippage(self):
        pass


class TestRewardAndSlippageDatum(unittest.TestCase):
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
        return RewardAndSlippageDatum(
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


class TestProtocolFeeDatum(unittest.TestCase):
    """Test ProtocolFeeDatum"""

    def test_invalid_input(self):
        """Test that negative ETH and COW fee throw an error."""

        # invalid ETH fee
        with self.assertRaises(AssertionError):
            ProtocolFeeDatum(Address.from_int(1), -1, 0, False)

        # invalid COW fee
        with self.assertRaises(AssertionError):
            ProtocolFeeDatum(Address.from_int(1), 0, -1, False)

    def test_as_payout(self):
        """Test creation of transfer from ProtocolFeeDatum"""
        fee_eth = 10**16
        self.assertEqual(
            ProtocolFeeDatum(Address.from_int(1), fee_eth, 0, False).as_payout(),
            Transfer(
                token=None,
                recipient=Address.from_int(1),
                amount_wei=fee_eth,
            ),
        )


if __name__ == "__main__":
    unittest.main()
