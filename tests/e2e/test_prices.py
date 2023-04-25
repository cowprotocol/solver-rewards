import unittest
from datetime import datetime, timedelta

from src.fetch.prices import (
    eth_in_token,
    TokenId,
    token_in_eth,
    token_in_usd,
    usd_price,
)

ONE_ETH = 10**18
DELTA = 0.00001


class TestPrices(unittest.TestCase):
    def setUp(self) -> None:
        self.some_date = datetime.strptime("2023-02-01", "%Y-%m-%d")
        self.cow_price = usd_price(TokenId.COW, self.some_date)
        self.eth_price = usd_price(TokenId.ETH, self.some_date)
        self.usdc_price = usd_price(TokenId.USDC, self.some_date)

    def test_usd_price(self):
        self.assertEqual(self.usdc_price, 1.000519)
        self.assertEqual(self.eth_price, 1590.48)
        self.assertEqual(self.cow_price, 0.098138)

    def test_token_in_usd(self):
        with self.assertRaises(AssertionError):
            token_in_usd(TokenId.COW, ONE_ETH, datetime.today())

        self.assertEqual(
            token_in_usd(TokenId.ETH, ONE_ETH, self.some_date), self.eth_price
        )
        self.assertEqual(
            token_in_usd(TokenId.COW, ONE_ETH, self.some_date), self.cow_price
        )
        self.assertEqual(
            token_in_usd(TokenId.USDC, 10**6, self.some_date), self.usdc_price
        )

    def test_eth_in_token(self):
        self.assertAlmostEqual(
            eth_in_token(TokenId.COW, ONE_ETH, self.some_date) / 10**18,
            self.eth_price / self.cow_price,
            delta=DELTA,
        )
        self.assertAlmostEqual(
            eth_in_token(TokenId.USDC, ONE_ETH, self.some_date) / 10**6,
            self.eth_price / self.usdc_price,
            delta=DELTA,
        )

    def test_token_in_eth(self):
        self.assertAlmostEqual(
            token_in_eth(TokenId.COW, ONE_ETH, self.some_date),
            10**18 * self.cow_price // self.eth_price,
            delta=DELTA,
        )
        self.assertAlmostEqual(
            token_in_eth(TokenId.USDC, 10**6, self.some_date),
            10**18 * self.usdc_price // self.eth_price,
            delta=DELTA,
        )

    def test_price_cache(self):
        # First call logs
        day = datetime.strptime("2022-03-10", "%Y-%m-%d")  # A date we used yet!
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
