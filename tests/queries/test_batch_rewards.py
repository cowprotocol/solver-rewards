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
                    "0x03",
                    "0x5111111111111111111111111111111111111111",
                    "0x5222222222222222222222222222222222222222",
                    "0x5333333333333333333333333333333333333333",
                ],
                "primary_reward_eth": [
                    2000000000000000.0,
                    3000000000000000.0,
                    3500000000000000.0,
                    28000000000000000.0,
                    12000000000000000.0,
                    -10000000000000000.0,
                ],
                "protocol_fee_eth": [
                    1250000000000000.0,  # 0.5 / (1 - 0.5) * 1e18 * 5e14 / 1e18 + 0.0045 / (1 - 0.0045) * 95e18 * 5e14 / 1e18
                    1000000000000000.0,  # 0.75 / (1 - 0.75) * 1e6 * 5e26 / 1e18 + 0.01 / (1 + 0.01) * 105e6 * 5e26 / 1e18
                    2000000000000000.0,  # 0.5 / (1 - 0.5) * 0.5e18 * 5e14 / 1e18 + 0.5 / (1 - 0.5) * 1e6 * 5e26 / 1e18 + 0.01 / (1 - 0.01) * 95e18 * 5e14 / 1e18
                    0.0,
                    0.0,
                    0.0,
                ],
                "network_fee_eth": [
                    4792548202188630.0,  # around 2 * 6_000_000 * 5e26 / 1e18 - 1250000000000000.0
                    5000000000000000.0,  # around 2 * 6_000_000 * 5e26 / 1e18 - 1000000000000000.0
                    10015762063681600.0,  # around 4 * 6_000_000 * 5e26 / 1e18 - 2000000000000000.0
                    0.0,  # zero due to missing surplus fee data
                    0.0,
                    0.0,
                ],
                "partner_list": [
                    ["0x90a48d5cf7343b08da12e067680b4c6dbfe551be"],
                    None,
                    None,
                    None,
                    None,
                    None,
                ],
                "partner_fee_eth": [
                    [250000000000000.0],
                    None,
                    None,
                    None,
                    None,
                    None,
                ],
            }
        )
        self.assertIsNone(pandas.testing.assert_frame_equal(expected, batch_rewards))


if __name__ == "__main__":
    unittest.main()
