import os
import unittest

import pandas.testing
from dotenv import load_dotenv
from pandas import DataFrame

from src.pg_client import MultiInstanceDBFetcher
from tests.db.pg_client import connect_and_populate_db_from


class TestBatchRewards(unittest.TestCase):
    def setUp(self) -> None:
        db_url = "postgresql+psycopg2://postgres:postgres@localhost:5432/postgres"
        self.fetcher = MultiInstanceDBFetcher([db_url])
        with open("./populate_cip_20.sql", "r", encoding="utf-8") as file:
            self.fetcher.connections[0].execute(file.read())

    def test_get_batch_rewards(self):
        start_block, end_block = "0", "100"
        batch_rewards = self.fetcher.get_solver_rewards(start_block, end_block)
        expected = DataFrame(
            {
                "solver": ["0x5222", "0x5444", "0x5111", "0x5333"],
                "total_reward_eth": [
                    10450000000000000.00000,
                    0.00000,
                    600000000000000.00000,
                    -10000000000000000.00000,
                ],
                "total_execution_cost_eth": [
                    450000000000000.00000,
                    0.00000,
                    800000000000000.00000,
                    0.00000,
                ],
                "num_participating_batches": [
                    2,
                    6,
                    7,
                    7,
                ],
            }
        )
        self.assertIsNone(pandas.testing.assert_frame_equal(expected, batch_rewards))


if __name__ == "__main__":
    unittest.main()
