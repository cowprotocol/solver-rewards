import unittest

from web3 import Web3

from src.fetch.transfer_file import aggregate_orderbook_rewards, map_reward
import pandas as pd


class MyTestCase(unittest.TestCase):
    def test_aggregate_orderbook_rewards(self):
        solvers = ["0x1", "0x2", "0x2"]
        tx_hashes = ["0x001", "0x002", "0x003"]
        amounts = [0, 55, 47]
        orderbook_rewards = pd.DataFrame(
            {
                "solver": solvers,
                "tx_hash": tx_hashes,
                "amount": amounts,
            }
        )
        results = aggregate_orderbook_rewards(
            orderbook_rewards, risk_free_transactions={tx_hashes[1]}
        )
        expected = pd.DataFrame(
            {
                "receiver": ["0x1", "0x2"],
                "num_trades": [1, 2],
                "amount": [0, Web3().toWei(84, "ether")],
                "token_address": [
                    "0xDEf1CA1fb7FBcDC777520aa7f396b4E015F497aB",
                    "0xDEf1CA1fb7FBcDC777520aa7f396b4E015F497aB",
                ],
            }
        )

        self.assertIsNone(pd.testing.assert_frame_equal(expected, results))

    def test_map_reward(self):
        self.assertEqual(map_reward(0, True), 0)
        self.assertEqual(map_reward(0, False), 0)
        self.assertEqual(
            map_reward(1, True), 37, "Risk-free non-zero amount must be 37!"
        )
        self.assertEqual(map_reward(1, False), 1)


if __name__ == "__main__":
    unittest.main()
