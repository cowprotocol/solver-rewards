import unittest

import duneapi.types

from src.utils.token_details import get_token_decimals


class TestTokenDecimals(unittest.TestCase):
    def setUp(self) -> None:
        self.cow = "0xDEf1CA1fb7FBcDC777520aa7f396b4E015F497aB"
        self.usdc = "0xA0b86991c6218b36c1d19D4a2e9Eb0cE3606eB48"

    def test_token_decimals(self):
        self.assertEqual(get_token_decimals(self.cow), 18)
        self.assertEqual(get_token_decimals(self.usdc), 6)

        self.assertEqual(get_token_decimals(duneapi.types.Address(self.usdc)), 6)
        self.assertEqual(get_token_decimals(duneapi.types.Address(self.cow)), 18)

    def test_token_decimals_cache(self):
        new_token = "0x10245515d35BC525e3C0977412322BFF32382EF1"
        with self.assertLogs("src.utils.token_details", level="INFO"):
            get_token_decimals(new_token)

        with self.assertNoLogs("src.utils.token_details", level="INFO"):
            get_token_decimals(new_token)


if __name__ == "__main__":
    unittest.main()
