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
                    "0x5444444444444444444444444444444444444444",
                ],
                "primary_reward_eth": [
                    2000000000000000.0,
                    3000000000000000.0,
                    3500000000000000.0,
                    28000000000000000.0,
                    12000000000000000.0,
                    -10000000000000000.0,
                    0.0,
                ],
                "num_participating_batches": [
                    3,
                    3,
                    4,
                    7,
                    2,
                    7,
                    6,
                ],
                "protocol_fee_eth": [
                    714716223003516.0,  # 0.5 / (1 - 0.5) * 1e18 * 5e14 / 1e18 + 0.0045 / (1 - 0.0045) * 95e18 * 5e14 / 1e18
                    2.0198019801980198e15,  # 0.75 / (1 - 0.75) * 1e6 * 5e26 / 1e18 + 0.01 / (1 + 0.01) * 105e6 * 5e26 / 1e18
                    1229797979797980.0,  # 0.5 / (1 - 0.5) * 0.5e18 * 5e14 / 1e18 + 0.5 / (1 - 0.5) * 1e6 * 5e26 / 1e18 + 0.01 / (1 - 0.01) * 95e18 * 5e14 / 1e18
                    0.0,
                    0.0,
                    0.0,
                    0.0,
                ],
                "network_fee_eth": [
                    7321857670537219.0,  # almost 2500000000000000 + 3000000000000000 + 2500000000000000 - 6.781...1e14
                    6980198019801980.0,  # 2500000000000000 + 4000000000000000 + 2500000000000000 - 2.0198019801980198e15
                    8779179226823198.0,
                    1050000000000000.0,
                    400000000000000.0,
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
                    None,
                ],
                "partner_fee_eth": [
                    [214716223003516],
                    None,
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
