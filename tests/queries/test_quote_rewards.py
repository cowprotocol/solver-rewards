import unittest

import pandas.testing
from pandas import DataFrame
from sqlalchemy import text

from src.pg_client import MultiInstanceDBFetcher


class TestQuoteRewards(unittest.TestCase):
    def setUp(self) -> None:
        db_url = "postgres:postgres@localhost:5432/postgres"
        self.fetcher = MultiInstanceDBFetcher([db_url])
        with open(
            "./tests/queries/quote_rewards_test_db.sql", "r", encoding="utf-8"
        ) as file:
            with self.fetcher.connections[0].connect() as connection:
                with connection.begin():
                    connection.execute(text(file.read()))

    def test_get_quote_rewards(self):
        start_block, end_block = "0", "100"
        quote_rewards = self.fetcher.get_quote_rewards(start_block, end_block)
        expected = DataFrame(
            {
                "solver": [
                    "0x01",
                    "0x02",
                    "0x03",
                ],
                "num_quotes": [
                    1,
                    1,
                    2,
                ],
            }
        )
        self.assertIsNone(pandas.testing.assert_frame_equal(expected, quote_rewards))


if __name__ == "__main__":
    unittest.main()
