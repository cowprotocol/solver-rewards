import os
import unittest

from dotenv import load_dotenv

from src.pg_client import OrderbookFetcher


class TestBatchRewards(unittest.TestCase):
    def setUp(self) -> None:
        # TODO - SETUP A SECOND DB
        load_dotenv()
        host = os.environ["BARN_ORDERBOOK_HOST"]
        port = os.environ["BARN_ORDERBOOK_PORT"]
        database = os.environ["BARN_ORDERBOOK_DB"]
        user = os.environ["BARN_ORDERBOOK_USER"]
        password = os.environ["BARN_ORDERBOOK_PASSWORD"]
        base = "postgresql+psycopg2"
        os.environ[
            "BARN_DB_URL"
        ] = f"{base}://{user}:{password}@{host}:{port}/{database}"
        os.environ[
            "PROD_DB_URL"
        ] = f"{base}://postgres:postgres@localhost:5432/postgres"

    def test_get_batch_rewards(self):

        start_block, end_block = "0", "10"
        batch_rewards = OrderbookFetcher.get_solver_rewards(start_block, end_block)
        print(batch_rewards)


if __name__ == "__main__":
    unittest.main()
