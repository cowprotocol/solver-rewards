from datetime import date, timedelta
import unittest

from src.utils.script_args import previous_tuesday


class TestPreviousTuesday(unittest.TestCase):
    def test_previous_tuesday(self):
        some_tuesday = date(year=2020, month=3, day=10)
        assert some_tuesday.weekday() == 1, "Tuesday week day is 1"
        backwards_expected = some_tuesday - timedelta(days=7)

        # going backward from tuesday (inclusive):
        for i in range(7):
            self.assertEqual(
                backwards_expected,
                previous_tuesday(some_tuesday - timedelta(days=i)),
                f"Failed at index {i}",
            )
        # going forward from tuesday (exclusive):
        forward_expected = some_tuesday
        for i in range(1, 7):
            self.assertEqual(
                previous_tuesday(some_tuesday + timedelta(days=i)), forward_expected
            )

        self.assertEqual(str(some_tuesday), '2020-03-10')
