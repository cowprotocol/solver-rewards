import unittest

import pandas.testing
from pandas import DataFrame

from src.pg_client import MultiInstanceDBFetcher


class TestBatchRewards(unittest.TestCase):
    def setUp(self) -> None:
        db_url = "postgres:postgres@localhost:5432/postgres"
        self.fetcher = MultiInstanceDBFetcher([db_url])
        with open("./populate_test_db.sql", "r", encoding="utf-8") as file:
            self.fetcher.connections[0].execute(file.read())

    def test_get_batch_rewards(self):
        start_block, end_block = "0", "100"
        batch_rewards = self.fetcher.get_quote_rewards(start_block, end_block)
        expected = DataFrame(
            {
                "solver": [
                    "0x5111111111111111111111111111111111111111",
                    "0x5333333333333333333333333333333333333333",
                    "0x5444444444444444444444444444444444444444",
                ],
                "num_quotes": [
                    1,
                    2,
                    1,
                ],
            }
        )
        self.assertIsNone(pandas.testing.assert_frame_equal(expected, batch_rewards))


if __name__ == "__main__":
    unittest.main()
