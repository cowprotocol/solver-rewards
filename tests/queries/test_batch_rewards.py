import unittest

import pandas.testing
from pandas import DataFrame

from src.pg_client import MultiInstanceDBFetcher


class TestBatchRewards(unittest.TestCase):
    def setUp(self) -> None:
        db_url = "postgres:postgres@localhost:5432/postgres"
        self.fetcher = MultiInstanceDBFetcher([db_url])
        with open(
            "./tests/queries/batch_rewards_test_db.sql", "r", encoding="utf-8"
        ) as file:
            self.fetcher.connections[0].execute(file.read())

    def test_get_batch_rewards(self):
        start_block, end_block = "0", "100"
        batch_rewards = self.fetcher.get_solver_rewards(start_block, end_block)
        expected = DataFrame(
            {
                "solver": [
                    "0x01",
                    "0x02",
                    "0x5111111111111111111111111111111111111111",
                    "0x5222222222222222222222222222222222222222",
                    "0x5333333333333333333333333333333333333333",
                    "0x5444444444444444444444444444444444444444",
                ],
                "payment_eth": [
                    9.534313722772278e15,
                    10.5e15,
                    600000000000000.00000,
                    10450000000000000.00000,
                    -10000000000000000.00000,
                    0.00000,
                ],
                "execution_cost_eth": [
                    7500000000000000.0,
                    7500000000000000.0,
                    800000000000000.00000,
                    450000000000000.00000,
                    0.00000,
                    0.00000,
                ],
                "num_participating_batches": [
                    3,
                    3,
                    7,
                    2,
                    7,
                    6,
                ],
                "protocol_fee_eth": [
                    5.748876684972541e14,  # 0.5 / (1 - 0.5) * 1e18 * 5e14 / 1e18 + 0.0015 / (1 + 0.0015) * 1e8 * 5e26 / 1e18
                    2.0198019801980198e15,  # 0.75 / (1 - 0.75) * 1e6 * 5e26 / 1e18 + 0.01 / (1 + 0.01) * 105e6 * 5e26 / 1e18
                    0.0,
                    0.0,
                    0.0,
                    0.0,
                ],
            }
        )
        self.assertIsNone(pandas.testing.assert_frame_equal(expected, batch_rewards))


if __name__ == "__main__":
    unittest.main()
