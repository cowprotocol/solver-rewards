"""
An interface for fetching prices.
Currently, only price feed is CoinPaprika's Free tier API.
"""
from enum import Enum
from typing import Optional
from datetime import datetime

from coinpaprika import client as cp


client = cp.Client()


# Note - we can get historical prices with the free tier and the following stipulation
# https://api.coinpaprika.com/#operation/getTickersHistoricalById:
# However their documentation seems outdated.
# and can only get hourly historical for last 24 hours.
# Example: client.historical("btc-bitcoin", start="2019-04-11T00:00:00Z")


class QuoteToken(Enum):
    """Coin Ids for coin paprika"""

    COW = "cow-cow-protocol-token"
    USD = "usdc-usd-coin"


def eth_in_token(
    token: QuoteToken, amount: float, day: Optional[datetime] = None
) -> float:
    """
    Compute how much of `token` is equivalent to `amount` ETH on `day`.
    Use current price if day not specified.
    """
    if day:
        response_list = client.historical(
            coin_id="eth-ethereum", start=day.strftime("%Y-%m-%d"), interval="1d"
        )
        for item in response_list:
            price_time = datetime.strptime(item["timestamp"], "%Y-%m-%dT00:00:00Z")
            if price_time == day:
                # TODO - THIS IS INCORRECT! FIX IT.
                usd_price = item["price"]

    return client.price_converter(
        base_currency_id="eth-ethereum",
        quote_currency_id=token.value,
        amount=amount,
    )["price"]


# This may not be entirely accurate, but the CoinPaprika API only supports
# historical quotes for arbitrary coins in USD or BTC. So we use the inverse.
def token_in_eth(
    token: QuoteToken, amount: float, start: Optional[datetime] = None
) -> float:
    """
    The inverse of eth_in_token;
    how much ETH is equivalent to `amount` of `token` on `day`
    """
    return 1 / eth_in_token(token, amount, start)
