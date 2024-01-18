import unittest

import pandas.testing
from pandas import DataFrame

from src.pg_client import MultiInstanceDBFetcher


class TestProtocolFees(unittest.TestCase):
    def setUp(self) -> None:
        db_url = "postgres:postgres@localhost:5432/postgres"
        self.fetcher = MultiInstanceDBFetcher([db_url])
        with open(
            "./tests/queries/protocol_fee_test_db.sql", "r", encoding="utf-8"
        ) as file:
            self.fetcher.connections[0].execute(file.read())

    def test_get_protocol_fees(self):
        start_block, end_block = "0", "100"
        protocol_fees = self.fetcher.get_protocol_fees(start_block, end_block)
        expected = DataFrame(
            {
                "solver": [
                    "0x01",
                    "0x02",
                ],
                "protocol_fee": [
                    5.751126690035052e14,
                    2.0303030303030302e15,
                ],
                "network_fee_correction": [
                    -540798946231228.0,
                    -2030303030303030.5,
                ],
            }
        )
        self.assertIsNone(pandas.testing.assert_frame_equal(expected, protocol_fees))


if __name__ == "__main__":
    unittest.main()
