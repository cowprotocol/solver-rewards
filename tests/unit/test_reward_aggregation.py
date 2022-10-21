import unittest

import pandas.testing
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
                "amount": [0, Web3().toWei(84, 'ether')],
                "token_address": [
                    "0xDEf1CA1fb7FBcDC777520aa7f396b4E015F497aB",
                    "0xDEf1CA1fb7FBcDC777520aa7f396b4E015F497aB",
                ],
            }
        )

        self.assertIsNone(pd.testing.assert_frame_equal(expected, results))


if __name__ == "__main__":
    unittest.main()
