import unittest

from web3 import Web3

from src.fetch.transfer_file import aggregate_orderbook_rewards, map_reward
import pandas as pd


def to_wei(t) -> int:
    return Web3().toWei(t, "ether")


class MyTestCase(unittest.TestCase):
    def test_aggregate_orderbook_rewards(self):
        # Tx 0x001 is 0x72e4c54e9c9dc2ee2a09dd242bf80abc39d122af0813ff4d570d3ce04eea8468
        # Tx 0x002 is 0x43bfe76d590966c7539f1ea0bb7989edc1289f989eaf8d84589c3508c5066c2c
        # Tx 0x003 is 0x6b6181e95ae837376dd15adbe7801bffffee639dbc8f18b918ace9645a5c1be2
        solvers = ["0x1", "0x1", "0x2", "0x2", "0x3", "0x1", "0x2", "0x3"]
        tx_hashes = [
            "0x001",
            "0x001",
            "0x002",
            "0x002",
            "0x003",
            "0x004",
            "0x005",
            "0x006",
        ]
        amounts = [39, 0, 40, 0, 41, 50, 60, 70]
        safe_liquidity = [None, True, None, False, None, None, None, None]
        orderbook_rewards = pd.DataFrame(
            {
                "solver": solvers,
                "tx_hash": tx_hashes,
                "amount": amounts,
                "safe_liquidity": safe_liquidity,
            }
        )
        results = aggregate_orderbook_rewards(
            orderbook_rewards, risk_free_transactions={"0x001", "0x002", "0x003"}
        )
        expected = pd.DataFrame(
            {
                "receiver": ["0x1", "0x2", "0x3"],
                "num_trades": [3, 3, 2],
                "amount": [to_wei(87), to_wei(100), to_wei(107)],
                "token_address": [
                    "0xDEf1CA1fb7FBcDC777520aa7f396b4E015F497aB",
                    "0xDEf1CA1fb7FBcDC777520aa7f396b4E015F497aB",
                    "0xDEf1CA1fb7FBcDC777520aa7f396b4E015F497aB",
                ],
            }
        )
        self.assertIsNone(pd.testing.assert_frame_equal(expected, results))

    def test_map_reward(self):
        self.assertEqual(map_reward(0, True, True), 0)
        self.assertEqual(map_reward(0, True, False), 0)
        self.assertEqual(map_reward(0, False, True), 0)
        self.assertEqual(map_reward(0, False, False), 0)

        self.assertEqual(map_reward(1, True, False), 37)
        self.assertEqual(map_reward(1, True, True), 1)
        self.assertEqual(map_reward(1, False, True), 1)
        self.assertEqual(map_reward(1, False, False), 1)


if __name__ == "__main__":
    unittest.main()
