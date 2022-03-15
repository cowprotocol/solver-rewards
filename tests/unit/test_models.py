import unittest

from src.models import Address, TransferType


class TestAddress(unittest.TestCase):
    def setUp(self) -> None:
        self.lower_case_address = '0xde1c59bc25d806ad9ddcbe246c4b5e5505645718'
        self.check_sum_address = '0xDEf1CA1fb7FBcDC777520aa7f396b4E015F497aB'
        self.invalid_address = '0x12'

    def test_invalid(self):
        with self.assertRaises(ValueError):
            Address(address=self.invalid_address)

    def test_valid(self):
        self.assertEqual(
            Address(address=self.lower_case_address).address,
            '0xdE1c59Bc25D806aD9DdCbe246c4B5e5505645718'
        )
        self.assertEqual(
            Address(address=self.check_sum_address).address,
            '0xDEf1CA1fb7FBcDC777520aa7f396b4E015F497aB'
        )


class TestTransferType(unittest.TestCase):
    def setUp(self) -> None:
        self.in_user_upper = 'IN_USER'
        self.in_amm_lower = 'in_amm'
        self.out_user_mixed = 'Out_User'
        self.invalid_type = 'invalid'

    def test_valid(self):
        self.assertEqual(
            TransferType.from_str(self.in_user_upper),
            TransferType.IN_USER
        )
        self.assertEqual(
            TransferType.from_str(self.in_amm_lower),
            TransferType.IN_AMM
        )
        self.assertEqual(
            TransferType.from_str(self.out_user_mixed),
            TransferType.OUT_USER
        )

    def test_invalid(self):
        with self.assertRaises(ValueError):
            TransferType.from_str(self.invalid_type)


if __name__ == '__main__':
    unittest.main()
