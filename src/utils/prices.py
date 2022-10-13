"""
An interface for fetching prices.
Currently, only price feed is CoinPaprika's Free tier API.
"""
import functools
import logging.config
from datetime import datetime
from enum import Enum

from coinpaprika import client as cp

from constants import LOG_CONFIG_FILE

log = logging.getLogger(__name__)
logging.config.fileConfig(
    fname=LOG_CONFIG_FILE.absolute(), disable_existing_loggers=False
)

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

    def decimals(self) -> int:
        """Decimals for each of the token variants."""
        if self == TokenId.USDC:
            return 6
        return 18


def eth_in_token(quote_token: TokenId, amount: int, day: datetime) -> int:
    """
    Compute how much of `token` is equivalent to `amount` ETH on `day`.
    Use current price if day not specified.
    """
    eth_amount_usd = token_in_usd(TokenId.ETH, amount, day)
    quote_price_usd = token_in_usd(quote_token, 10 ** quote_token.decimals(), day)
    return int(eth_amount_usd / quote_price_usd * 10 ** quote_token.decimals())


def token_in_eth(token: TokenId, amount: int, day: datetime) -> int:
    """
    The inverse of eth_in_token;
    how much ETH is equivalent to `amount` of `token` on `day`
    """
    token_amount_usd = token_in_usd(token, amount, day)
    eth_price_usd = token_in_usd(TokenId.ETH, 10 ** TokenId.ETH.decimals(), day)

    return int(token_amount_usd / eth_price_usd * 10 ** TokenId.ETH.decimals())


def token_in_usd(token: TokenId, amount_wei: int, day: datetime) -> float:
    """
    Converts token amount [wei] to usd amount on given day.
    """
    return float(amount_wei) * usd_price(token, day) / 10.0 ** token.decimals()


@functools.cache
def usd_price(token: TokenId, day: datetime) -> float:
    """
    A cached version of CoinPaprika's API request.
    This will only ever make an API request on unique (token, day) pairs
    """
    log.info("requesting price for token=%s, day=%s", token.value, day.date())
    response_list = client.historical(
        coin_id=token.value, start=day.strftime("%Y-%m-%d"), limit=1, interval="1d"
    )
    assert (
        len(response_list) == 1
    ), f"invalid results for usd price on date {day} - got {response_list}"
    item = response_list[0]
    price_time = datetime.strptime(item["timestamp"], "%Y-%m-%dT00:00:00Z")
    assert price_time == day
    return float(item["price"])
