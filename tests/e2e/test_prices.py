import unittest
from datetime import datetime, timedelta

from src.utils.prices import (
    eth_in_token,
    TokenId,
    token_in_eth,
    token_in_usd,
    usd_price,
)


class TestPrices(unittest.TestCase):
    def setUp(self) -> None:
        self.far_past = datetime.strptime("2022-01-01", "%Y-%m-%d")
        # https://api.coinpaprika.com/v1/tickers/cow-cow-protocol-token/historical?start=2022-01-01&interval=1d&end=2022-04-16
        self.first_cow_day = datetime.strptime("2022-04-15", "%Y-%m-%d")
        self.day_before_cow = self.first_cow_day - timedelta(days=1)

    def test_token_in_usd(self):
        with self.assertRaises(AssertionError):
            token_in_usd(TokenId.COW, 1, self.day_before_cow)

        with self.assertRaises(AssertionError):
            token_in_usd(TokenId.COW, 1, datetime.today())

        self.assertEqual(token_in_usd(TokenId.ETH, 1, self.first_cow_day), 3032.45)
        self.assertEqual(token_in_usd(TokenId.COW, 1, self.first_cow_day), 0.435229)
        self.assertEqual(token_in_usd(TokenId.USDC, 1, self.first_cow_day), 1.001656)

    def test_eth_in_token(self):
        with self.assertRaises(AssertionError):
            eth_in_token(TokenId.COW, 1, self.day_before_cow)

        # cow_price =  0.435229
        # eth_price = 3032.45
        # usdc_price = 1.001656
        self.assertAlmostEqual(
            eth_in_token(TokenId.COW, 1, self.first_cow_day),
            3032.45 / 0.435229,
            delta=0.0001,
        )
        self.equal = self.assertAlmostEqual(
            eth_in_token(TokenId.USDC, 1, self.first_cow_day),
            3032.45 / 1.001656,
            delta=0.0001,
        )

    def test_token_in_eth(self):
        with self.assertRaises(AssertionError):
            token_in_eth(TokenId.COW, 1, self.day_before_cow)

        # cow_price =  0.435229
        # eth_price = 3032.45
        # usdc_price = 1.001656
        self.assertAlmostEqual(
            token_in_eth(TokenId.COW, 1, self.first_cow_day),
            0.435229 / 3032.45,
            delta=0.0001,
        )
        self.assertAlmostEqual(
            token_in_eth(TokenId.USDC, 1, self.first_cow_day),
            1.001656 / 3032.45,
            delta=0.0001,
        )

    def test_price_cache(self):
        # First call logs
        day = datetime.strptime("2022-03-10", "%Y-%m-%d")  # A date we used yet!
        token = TokenId.USDC
        with self.assertLogs("src.utils.prices", level="INFO") as cm:
            usd_price(token, day)
        expected_msg = f"requesting price for token={token.value}, day={day.date()}"
        self.assertEqual(
            cm.output,
            [f"INFO:src.utils.prices:{expected_msg}"],
        )
        # Second call does not log.
        with self.assertNoLogs("src.utils.prices", level="INFO"):
            usd_price(token, day)


if __name__ == "__main__":
    unittest.main()
