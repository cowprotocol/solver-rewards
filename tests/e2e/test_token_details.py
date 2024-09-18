import unittest

from dune_client.types import Address
from web3 import Web3

from src.utils.token_details import get_token_decimals

W3 = Web3(Web3.HTTPProvider("https://rpc.ankr.com/eth_sepolia"))


class TestTokenDecimals(unittest.TestCase):
    def test_token_decimals(self):
        usdc = "0x1c7D4B196Cb0C7B01d743Fbc6116a902379C7238"
        self.assertEqual(get_token_decimals(W3, usdc), 6)
        self.assertEqual(get_token_decimals(W3, Address(usdc)), 6)

    def test_token_decimals_cache(self):
        new_token = "0x0625afb445c3b6b7b929342a04a22599fd5dbb59"
        with self.assertLogs("src.utils.token_details", level="INFO"):
            get_token_decimals(W3, new_token)

        with self.assertNoLogs("src.utils.token_details", level="INFO"):
            get_token_decimals(W3, new_token)


if __name__ == "__main__":
    unittest.main()
