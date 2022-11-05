import unittest
from dataclasses import dataclass

from src.models.accounting_period import AccountingPeriod
from src.utils.dataset import index_by


@dataclass
class DummyDataClass:
    x: int
    y: str


class TestDataUtils(unittest.TestCase):
    def test_dashboard_url(self):
        expected = (
            "https://dune.com/gnosis.protocol/solver-rewards-accounting-v2?"
            "StartTime=2022-05-31+00%3A00%3A00&"
            "EndTime=2022-06-07+00%3A00%3A00&"
        )
        result = AccountingPeriod("2022-05-31").dashboard_url()
        self.assertEqual(
            expected,
            result,
        )

    def test_index_by(self):
        data_set = [
            DummyDataClass(1, "a"),
            DummyDataClass(2, "b"),
            DummyDataClass(3, "b"),
        ]
        expected = {1: data_set[0], 2: data_set[1], 3: data_set[2]}
        self.assertEqual(index_by(data_set, "x"), expected)

        with self.assertRaises(IndexError) as err:
            index_by(data_set, "y")

        self.assertEqual(
            str(err.exception), 'Attempting to index by non-unique index key "b"'
        )
        bad_field = "xxx"
        with self.assertRaises(AssertionError) as err:
            index_by(data_set, bad_field)
        self.assertEqual(
            str(err.exception),
            f"<class 'test_data_utils.DummyDataClass'> has no field \"{bad_field}\"",
        )


if __name__ == "__main__":
    unittest.main()
