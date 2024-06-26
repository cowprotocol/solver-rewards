import unittest

from pandas import Series

from src.fetch.rewards import (
    compute_primary_reward_datum,
    is_market_order,
    EPSILON_UPPER,
    EPSILON_LOWER,
)


class TestRewards(unittest.TestCase):
    def test_is_market_order(self):
        """Test in market check"""

        def create_test_trade(
            kind: str,
            partially_fillable: bool,
            limit_sell_amount: int,
            limit_buy_amount: int,
        ):
            return Series(
                {
                    "winning_solver": "0x0001",
                    "auction_id": 0,
                    "order_uid": "0x01",
                    "kind": kind,
                    "partially_fillable": partially_fillable,
                    "limit_sell_amount": limit_sell_amount,
                    "limit_buy_amount": limit_buy_amount,
                    # quote corresponds to 100 DAI to 100 USDC for a fee of 5 DAI
                    "quote_sell_amount": 100 * 10**18,
                    "quote_buy_amount": 100 * 10**6,
                    "quote_gas_amount": 25 * 10**4,
                    "quote_gas_price": 10 * 10**9,
                    "quote_sell_token_price": 5 * 10**14 / 10**18,
                    "quote_solver": "0x0002",
                }
            ).astype(object)

        # sell orders
        # buy amount = quote - costs - slippage: in market
        self.assertTrue(
            is_market_order(
                create_test_trade("sell", False, 100 * 10**18, 94 * 10**6)
            )
        )
        # buy amount = quote - cost, 0 slippage: in market
        self.assertTrue(
            is_market_order(
                create_test_trade("sell", False, 100 * 10**18, 95 * 10**6)
            )
        )
        # buy amount =  quote te costs + 1: not in market
        self.assertFalse(
            is_market_order(
                create_test_trade("sell", False, 100 * 10**18, 96 * 10**6)
            )
        )
        # buy amount =  quote - costs - slippage but partially fillable: not in market
        self.assertFalse(
            is_market_order(
                create_test_trade("sell", True, 100 * 10**18, 94 * 10**6)
            )
        )

        # buy orders
        # sell amount = quote + costs + slippage: in market
        self.assertTrue(
            is_market_order(
                create_test_trade("buy", False, 106 * 10**18, 100 * 10**6)
            )
        )
        # sell amount = quote + cost, 0 slippage: in market
        self.assertTrue(
            is_market_order(
                create_test_trade("buy", False, 105 * 10**18, 95 * 10**6)
            )
        )
        # sell amount =  quote + costs - 1: not in market
        self.assertFalse(
            is_market_order(
                create_test_trade("buy", False, 104 * 10**18, 96 * 10**6)
            )
        )
        # sell amount = quote + costs + slippage but partially fillable: not in market
        self.assertFalse(
            is_market_order(
                create_test_trade("buy", True, 106 * 10**18, 100 * 10**6)
            )
        )

    # TODO: Implement these tests, see issue #361
    def test_compute_solver_rewards(self):
        pass

    def test_compute_primary_rewards(self):
        pass

    def test_compute_primary_reward_datum(self):
        # no revert, not capped
        row = Series(
            {
                "tx_hash": "0x01",
                "winning_solver": "0x0001",
                "winning_score": 10**17,
                "reference_score": 95 * 10**15,
            }
        )
        self.assertEqual(compute_primary_reward_datum(row), ("0x0001", 5 * 10**15))
        # no revert, capped
        row = Series(
            {
                "tx_hash": "0x01",
                "winning_solver": "0x0001",
                "winning_score": 10**17,
                "reference_score": 5 * 10**15,
            }
        )
        self.assertEqual(compute_primary_reward_datum(row), ("0x0001", EPSILON_UPPER))
        # revert, not capped
        row = Series(
            {
                "tx_hash": None,
                "winning_solver": "0x0001",
                "winning_score": 10**17,
                "reference_score": 5 * 10**15,
            }
        )
        self.assertEqual(compute_primary_reward_datum(row), ("0x0001", -5 * 10**15))
        # revert, capped
        row = Series(
            {
                "tx_hash": None,
                "winning_solver": "0x0001",
                "winning_score": 10**17,
                "reference_score": 95 * 10**15,
            }
        )
        self.assertEqual(compute_primary_reward_datum(row), ("0x0001", -EPSILON_LOWER))

    # TODO: Implement these tests, see issue #361
    def test_compute_secondary_rewards(self):
        pass

    def test_compute_quote_rewards(self):
        pass
