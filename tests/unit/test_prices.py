import unittest
from datetime import datetime

from coinpaprika.exceptions import CoinpaprikaAPIException

from src.utils.prices import eth_in_token, QuoteToken


class TestPrices(unittest.TestCase):
    def test_eth_in_token_on_date(self):
        past = datetime.strptime("2022-01-01", "%Y-%m-%d")
        self.assertAlmostEqual(
            eth_in_token(QuoteToken.COW, 1, past),
            3731.58,
            delta=0.001
        )

        # TODO - this is for hourly prices.
        # with self.assertRaises(CoinpaprikaAPIException) as err:
        #     # error: Getting hourly historical data before is not allowed in this plan.
        #     # Check plans on coinpaprika.com/api
        #     eth_in_token(QuoteToken.COW, 1, too_far_past)

        present = datetime.today()
        self.assertGreater(eth_in_token(QuoteToken.COW, 1, present), 0)

    def test_eth_in_token(self):
        self.assertGreater(eth_in_token(QuoteToken.COW, 1), 0)
        self.assertGreater(eth_in_token(QuoteToken.USD, 1), 0)


if __name__ == "__main__":
    unittest.main()
