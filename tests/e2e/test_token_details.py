import unittest

import dune_client.types
from web3 import Web3

from src.constants import INFURA_KEY
from src.utils.token_details import get_token_decimals

W3 = Web3(Web3.HTTPProvider(f"https://goerli.infura.io/v3/{INFURA_KEY}"))


class TestTokenDecimals(unittest.TestCase):
    def test_token_decimals(self):
        # Goerli doesn't seem to have tokens with anything other than 18 decimals.
        cow = "0x3430d04E42a722c5Ae52C5Bffbf1F230C2677600"
        self.assertEqual(get_token_decimals(W3, cow), 18)
        self.assertEqual(get_token_decimals(W3, dune_client.types.Address(cow)), 18)

    def test_token_decimals_cache(self):
        new_token = "0x40c92339fd9c0f59d976af127e82de61914efd0f"
        with self.assertLogs("src.utils.token_details", level="INFO"):
            get_token_decimals(W3, new_token)

        with self.assertNoLogs("src.utils.token_details", level="INFO"):
            get_token_decimals(W3, new_token)


if __name__ == "__main__":
    unittest.main()
