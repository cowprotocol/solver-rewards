import os
import unittest

import pandas.testing
from dotenv import load_dotenv
from pandas import DataFrame

from src.pg_client import OrderbookFetcher
from tests.db.pg_client import connect_and_populate_db_from


class TestBatchRewards(unittest.TestCase):
    def setUp(self) -> None:
        # TODO - Come up with a less hacky way of using only 1 DB
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
        connect_and_populate_db_from("./populate_cip_20.sql")
        start_block, end_block = "0", "100"
        batch_rewards = OrderbookFetcher.get_solver_rewards(start_block, end_block)
        print(batch_rewards)
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
                    2.00000,
                    6.00000,
                    7.00000,
                    7.00000,
                ],
            }
        )
        self.assertIsNone(pandas.testing.assert_frame_equal(expected, batch_rewards))


if __name__ == "__main__":
    unittest.main()
