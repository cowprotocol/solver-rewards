"""
An interface for fetching prices.
Currently, only price feed is CoinPaprika's Free tier API.
"""

import functools
import logging.config
from datetime import datetime
from enum import Enum
from fractions import Fraction

from coinpaprika import client as cp
from dune_client.types import Address

from src.config import IOConfig

log = logging.getLogger(__name__)
logging.config.fileConfig(
    fname=IOConfig.from_env().log_config_file.absolute(), disable_existing_loggers=False
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


TOKEN_ADDRESS_TO_ID = {
    Address("0xc02aaa39b223fe8d0a0e5c4f27ead9083c756cc2"): TokenId.ETH,
    Address("0xDEf1CA1fb7FBcDC777520aa7f396b4E015F497aB"): TokenId.COW,
    Address("0xa0b86991c6218b36c1d19d4a2e9eb0ce3606eb48"): TokenId.USDC,
}


def exchange_rate_atoms(
    token_1_address: Address, token_2_address: Address, day: datetime
) -> Fraction:
    """Exchange rate for converting tokens on a given day.
    The convention for the exchange rate r is as follows:
    x atoms of token 1 have the same value as x * r atoms of token 2.
    """
    token_1 = TOKEN_ADDRESS_TO_ID[token_1_address]
    token_2 = TOKEN_ADDRESS_TO_ID[token_2_address]
    price_1 = Fraction(usd_price(token_1, day)) / Fraction(10 ** token_1.decimals())
    price_2 = Fraction(usd_price(token_2, day)) / Fraction(10 ** token_2.decimals())
    return price_1 / price_2


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
