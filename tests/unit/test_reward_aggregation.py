import unittest

from web3 import Web3

import pandas as pd

from src.fetch.cow_rewards import aggregate_orderbook_rewards, map_reward


def to_wei(t) -> int:
    return Web3().to_wei(t, "ether")


class MyTestCase(unittest.TestCase):
    """
    This test is a mock dataset capturing the real data from
    cf: https://github.com/cowprotocol/solver-rewards/pull/107#issuecomment-1288566854
    """

    def test_aggregate_orderbook_rewards(self):
        solvers = [
            "0x1",
            "0x1",
            "0x2",
            "0x2",
            "0x3",
            "0x1",
            "0x2",
            "0x3",
            "0x4",
            "0x4",
            "0x4",
        ]
        tx_hashes = [
            # Tx 0x001 is 0x72e4c54e9c9dc2ee2a09dd242bf80abc39d122af0813ff4d570d3ce04eea8468
            "0x001",
            "0x001",
            # Tx 0x002 is 0x43bfe76d590966c7539f1ea0bb7989edc1289f989eaf8d84589c3508c5066c2c
            "0x002",
            "0x002",
            # Tx 0x003 is 0x6b6181e95ae837376dd15adbe7801bffffee639dbc8f18b918ace9645a5c1be2
            "0x003",
            "0x004",
            "0x005",
            "0x006",
            # Tx 0x007 0x82318dd23592f7ccba72fcad43c452c4c426d9e02c7cf3b1f9e7823a0c9a9fc0
            "0x007",
            "0x007",
            "0x007",
        ]
        amounts = [39, 0, 40, 0, 41, 50, 60, 70, 40, 50, 0]
        surplus_fees = [None] * len(amounts)
        orderbook_rewards = pd.DataFrame(
            {
                "solver": solvers,
                "tx_hash": tx_hashes,
                "surplus_fee": surplus_fees,
                "amount": amounts,
            }
        )
        results = aggregate_orderbook_rewards(
            orderbook_rewards,
            risk_free_transactions={"0x001", "0x002", "0x003", "0x007"},
        )
        expected = pd.DataFrame(
            {
                "receiver": ["0x1", "0x2", "0x3", "0x4"],
                "num_trades": [3, 3, 2, 3],
                "amount": [to_wei(87), to_wei(97), to_wei(107), to_wei(74)],
                "token_address": [
                    "0xDEf1CA1fb7FBcDC777520aa7f396b4E015F497aB",
                    "0xDEf1CA1fb7FBcDC777520aa7f396b4E015F497aB",
                    "0xDEf1CA1fb7FBcDC777520aa7f396b4E015F497aB",
                    "0xDEf1CA1fb7FBcDC777520aa7f396b4E015F497aB",
                ],
            }
        )
        print(expected)
        print(results)
        self.assertIsNone(pd.testing.assert_frame_equal(expected, results))

    def test_map_reward(self):
        self.assertEqual(map_reward(0, True), 0)
        self.assertEqual(map_reward(1, True), 37)
        self.assertEqual(map_reward(0, False), 0)
        self.assertEqual(map_reward(1, False), 1)


if __name__ == "__main__":
    unittest.main()
