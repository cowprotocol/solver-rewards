import datetime
import unittest

from src.fetch.block_number import get_block, Closest


class MyTestCase(unittest.TestCase):
    def test_get_block(self):
        # cf: https://etherscan.io/block/9640366
        before = get_block(datetime.datetime(2020, 3, 10, 1, 2, 3), Closest.BEFORE)
        after = get_block(datetime.datetime(2020, 3, 10, 1, 2, 3), Closest.AFTER)
        expected = 9640366
        self.assertEqual(before, expected)
        self.assertEqual(after, expected + 1)


if __name__ == "__main__":
    unittest.main()
