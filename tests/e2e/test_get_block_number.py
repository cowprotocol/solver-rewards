import os
import unittest

from dotenv import load_dotenv
from dune_client.client import DuneClient

from src.fetch.dune import DuneFetcher
from src.models.accounting_period import AccountingPeriod


class TestGetBlockNumber(unittest.TestCase):
    def setUp(self) -> None:
        load_dotenv()
        self.fetcher = DuneFetcher(
            DuneClient(os.environ["DUNE_API_KEY"]),
            "ethereum",
            AccountingPeriod("2022-10-18"),
        )

    def test_get_block_number(self):
        self.fetcher.period = AccountingPeriod("1970-01-01")  # Before Time
        self.assertEqual(self.fetcher.get_block_interval(), ("None", "None"))

        self.fetcher.period = AccountingPeriod(
            "2015-07-30", length_days=1
        )  # First block
        self.assertEqual(self.fetcher.get_block_interval(), ("1", "6911"))

        self.fetcher.period = AccountingPeriod(
            "2015-07-31", length_days=1
        )  # Day after first block
        self.assertEqual(
            self.fetcher.get_block_interval(),
            ("6912", "13774"),
        )


if __name__ == "__main__":
    unittest.main()
