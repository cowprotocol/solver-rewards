import unittest

from duneapi.api import DuneAPI

from src.fetch.dune import DuneFetcher
from src.models.accounting_period import AccountingPeriod


class TestGetBlockNumber(unittest.TestCase):
    def test_get_block_number(self):
        dune = DuneAPI.new_from_environment()
        before_time = AccountingPeriod("1970-01-01")
        self.assertEqual(
            DuneFetcher(dune, period=before_time).get_block_interval(), ("0", "0")
        )

        first_block = AccountingPeriod("2015-07-30", length_days=1)
        self.assertEqual(
            DuneFetcher(dune, period=first_block).get_block_interval(), ("1", "6911")
        )

        day_after_first_block = AccountingPeriod("2015-07-31", length_days=1)
        self.assertEqual(
            DuneFetcher(dune, period=day_after_first_block).get_block_interval(),
            ("6912", "13774"),
        )


if __name__ == "__main__":
    unittest.main()
