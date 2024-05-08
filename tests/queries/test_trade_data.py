import unittest


from src.pg_client import MultiInstanceDBFetcher


class TestTradeData(unittest.TestCase):
    def setUp(self) -> None:
        db_url = "postgres:postgres@localhost:5432/postgres"
        self.fetcher = MultiInstanceDBFetcher([db_url])
        with open(
            "./tests/queries/batch_rewards_test_db.sql", "r", encoding="utf-8"
        ) as file:
            self.fetcher.connections[0].execute(file.read())

    def test_get_trade_data(self):
        start_block, end_block = "0", "100"
        trade_data = self.fetcher.get_trade_data(start_block, end_block)
        print(trade_data)
        self.assertTrue(trade_data.size == 8 * 29)


if __name__ == "__main__":
    unittest.main()
