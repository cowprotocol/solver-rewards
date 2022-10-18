import unittest

import duneapi.types

from src.utils.token_details import get_token_decimals


class TestTokenDecimals(unittest.TestCase):
    def test_token_decimals(self):
        # Goerli doesn't seem to have tokens with anything other than 18 decimals.
        cow = "0x3430d04E42a722c5Ae52C5Bffbf1F230C2677600"
        self.assertEqual(get_token_decimals(cow), 18)
        self.assertEqual(get_token_decimals(duneapi.types.Address(cow)), 18)

    def test_token_decimals_cache(self):
        new_token = "0x10245515d35BC525e3C0977412322BFF32382EF1"
        with self.assertLogs("src.utils.token_details", level="INFO"):
            get_token_decimals(new_token)

        with self.assertNoLogs("src.utils.token_details", level="INFO"):
            get_token_decimals(new_token)


if __name__ == "__main__":
    unittest.main()
