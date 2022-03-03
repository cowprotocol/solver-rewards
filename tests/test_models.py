import unittest

from src.models import Account


class TransferClass(unittest.TestCase):
    def setUp(self) -> None:
        self.lower_case_address = '0xde1c59bc25d806ad9ddcbe246c4b5e5505645718'
        self.check_sum_address = '0xDEf1CA1fb7FBcDC777520aa7f396b4E015F497aB'
        self.invalid_address = '0x12'

    def test_invalid(self):
        with self.assertRaises(ValueError):
            Account(address=self.invalid_address)

    def test_valid(self):
        self.assertEqual(
            Account(address=self.lower_case_address).address,
            '0xdE1c59Bc25D806aD9DdCbe246c4B5e5505645718'
        )
        self.assertEqual(
            Account(address=self.check_sum_address).address,
            '0xDEf1CA1fb7FBcDC777520aa7f396b4E015F497aB'
        )


if __name__ == '__main__':
    unittest.main()
