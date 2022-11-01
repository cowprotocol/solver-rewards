import unittest

from duneapi.api import DuneAPI

from src.models.accounting_period import AccountingPeriod


class MyTestCase(unittest.TestCase):
    def test_get_block_number(self):
        dune = DuneAPI.new_from_environment()
        before_time = AccountingPeriod("1970-01-01")
        self.assertEqual(before_time.get_block_interval(dune), ("0", "0"))

        first_block_date = "2015-07-30"
        at_time = AccountingPeriod(first_block_date, length_days=1)
        self.assertEqual(at_time.get_block_interval(dune), ("1", "6911"))

        day_after_first_block = "2015-07-31"
        right_after_time = AccountingPeriod(day_after_first_block, length_days=1)
        self.assertEqual(right_after_time.get_block_interval(dune), ("6912", "13774"))


if __name__ == "__main__":
    unittest.main()
