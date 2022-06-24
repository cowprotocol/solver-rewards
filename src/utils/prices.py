"""
An interface for fetching prices.
Currently, only price feed is CoinPaprika's Free tier API.
"""
from enum import Enum
from datetime import datetime

from coinpaprika import client as cp


client = cp.Client()


# Note - we can get historical prices with the free tier and the following stipulation
# https://api.coinpaprika.com/#operation/getTickersHistoricalById:
# However their documentation seems outdated.
# and can only get hourly historical for last 24 hours.
# Example: client.historical("btc-bitcoin", start="2019-04-11T00:00:00Z")


class TokenId(Enum):
    """Coin Ids for coin paprika"""

    ETH = "eth-ethereum"
    COW = "cow-cow-protocol-token"
    USDC = "usdc-usd-coin"


def eth_in_token(quote_token: TokenId, amount: float, day: datetime) -> float:
    """
    Compute how much of `token` is equivalent to `amount` ETH on `day`.
    Use current price if day not specified.
    """
    eth_amount_usd = token_in_usd(TokenId.ETH, amount, day)
    quote_price_usd = token_in_usd(quote_token, 1, day)
    return eth_amount_usd / quote_price_usd


def token_in_eth(token: TokenId, amount: float, day: datetime) -> float:
    """
    The inverse of eth_in_token;
    how much ETH is equivalent to `amount` of `token` on `day`
    """
    token_amount_usd = token_in_usd(token, amount, day)
    eth_price_usd = token_in_usd(TokenId.ETH, 1, day)

    return token_amount_usd / eth_price_usd


def token_in_usd(token: TokenId, amount: float, day: datetime) -> float:
    """
    Converts token amount to usd amount on given day.
    """
    response_list = client.historical(
        coin_id=token.value, start=day.strftime("%Y-%m-%d"), limit=1, interval="1d"
    )
    assert len(response_list) == 1, "no results for usd price on date"
    item = response_list[0]
    price_time = datetime.strptime(item["timestamp"], "%Y-%m-%dT00:00:00Z")
    assert price_time == day
    return amount * float(item["price"])
