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


if __name__ == "__main__":
    unittest.main()
