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
        usdc = "0x5ffbac75efc9547fbc822166fed19b05cd5890bb"
        with self.assertLogs("src.utils.token_details", level="INFO"):
            get_token_decimals(usdc)

        with self.assertNoLogs("src.utils.token_details", level="INFO"):
            get_token_decimals(usdc)


if __name__ == "__main__":
    unittest.main()
