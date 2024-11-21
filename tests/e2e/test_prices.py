import unittest
from datetime import datetime

from dune_client.types import Address

from src.config import AccountingConfig, Network
from src.fetch.prices import (
    TokenId,
    exchange_rate_atoms,
    usd_price,
)

ONE_ETH = 10**18
DELTA = 0.00001


class TestPrices(unittest.TestCase):
    def setUp(self) -> None:
        self.config = AccountingConfig.from_network(Network.MAINNET)
        self.some_date = datetime.strptime("2024-09-01", "%Y-%m-%d")
        self.cow_price = usd_price(TokenId.COW, self.some_date)
        self.eth_price = usd_price(TokenId.ETH, self.some_date)
        self.usdc_price = usd_price(TokenId.USDC, self.some_date)
        self.cow_address = self.config.reward_config.reward_token_address
        self.weth_address = Address(self.config.payment_config.weth_address)
        self.usdc_address = Address("0xa0b86991c6218b36c1d19d4a2e9eb0ce3606eb48")

    def test_usd_price(self):
        self.assertEqual(self.usdc_price, 1.001622)
        self.assertEqual(self.eth_price, 2481.89)
        self.assertEqual(self.cow_price, 0.194899)

    def test_exchange_rate_atoms(self):
        with self.assertRaises(AssertionError):
            exchange_rate_atoms(self.cow_address, self.weth_address, datetime.today())

        self.assertEqual(
            exchange_rate_atoms(self.cow_address, self.cow_address, self.some_date), 1
        )
        self.assertEqual(
            exchange_rate_atoms(self.cow_address, self.weth_address, self.some_date),
            1
            / exchange_rate_atoms(self.weth_address, self.cow_address, self.some_date),
        )

        self.assertEqual(
            float(
                exchange_rate_atoms(self.cow_address, self.weth_address, self.some_date)
            ),
            self.cow_price / self.eth_price,
        )

        self.assertEqual(
            float(
                exchange_rate_atoms(self.cow_address, self.usdc_address, self.some_date)
            )
            * 10**18,
            self.cow_price / self.usdc_price * 10**6,
        )

    def test_price_cache(self):
        # First call logs
        day = datetime.strptime("2024-08-01", "%Y-%m-%d")  # A date we used yet!
        token = TokenId.USDC
        with self.assertLogs("src.fetch.prices", level="INFO") as cm:
            usd_price(token, day)
        expected_msg = f"requesting price for token={token.value}, day={day.date()}"
        self.assertEqual(
            cm.output,
            [f"INFO:src.fetch.prices:{expected_msg}"],
        )
        # Second call does not log.
        with self.assertNoLogs("src.utils.prices", level="INFO"):
            usd_price(token, day)


if __name__ == "__main__":
    unittest.main()
