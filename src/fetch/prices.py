"""
An interface for fetching prices.
Currently, only price feed is CoinPaprika's Free tier API.
"""

import functools
from datetime import datetime
from enum import Enum
from fractions import Fraction

from coinpaprika import client as cp
from dune_client.types import Address

from src.logger import set_log

log = set_log(__name__)

client = cp.Client()


# Note - we can get historical prices with the free tier and the following stipulation
# https://api.coinpaprika.com/#operation/getTickersHistoricalById:
# However their documentation seems outdated.
# and can only get hourly historical for last 24 hours.
# Example: client.historical("btc-bitcoin", start="2019-04-11T00:00:00Z")


class TokenId(Enum):
    """Coin Ids for coin paprika"""

    ETH = "eth-ethereum"
    XDAI = "dai-dai"
    COW = "cow-cow-protocol-token"
    USDC = "usdc-usd-coin"
    AVAX = "avax-avalanche"
    POL = "pol-polygon-ecosystem-token"
    GHO = "gho-gho"
    BNB = "bnb-bnb"
    XPL = "xpl-plasma"

    def decimals(self) -> int:
        """Decimals for each of the token variants."""
        if self == TokenId.USDC:
            return 6
        return 18


TOKEN_ADDRESS_TO_ID = {
    # mainnet COW address
    Address("0xDEf1CA1fb7FBcDC777520aa7f396b4E015F497aB"): TokenId.COW,
    # mainnet tokens
    Address("0xc02aaa39b223fe8d0a0e5c4f27ead9083c756cc2"): TokenId.ETH,
    Address("0xa0b86991c6218b36c1d19d4a2e9eb0ce3606eb48"): TokenId.USDC,
    # gnosis tokens
    Address("0x6a023ccd1ff6f2045c3309768ead9e68f978f6e1"): TokenId.ETH,
    Address("0xe91d153e0b41518a2ce8dd3d7944fa863463a97d"): TokenId.XDAI,
    # arbitrum tokens
    Address("0x82af49447d8a07e3bd95bd0d56f35241523fbab1"): TokenId.ETH,
    # base tokens
    Address("0x4200000000000000000000000000000000000006"): TokenId.ETH,
    # avalanche tokens
    Address("0xB31f66AA3C1e785363F0875A1B74E27b85FD66c7"): TokenId.AVAX,
    Address("0x49D5c2BdFfac6CE2BFdB6640F4F80f226bc10bAB"): TokenId.ETH,
    # polygon tokens
    Address("0x0d500B1d8E8eF31E21C99d1Db9A6444d3ADf1270"): TokenId.POL,
    Address("0x7ceB23fD6bC0adD59E62ac25578270cFf1b9f619"): TokenId.ETH,
    # lens tokens
    Address("0x6bDc36E20D267Ff0dd6097799f82e78907105e2F"): TokenId.GHO,
    Address("0xe5ecd226b3032910ceaa43ba92ee8232f8237553"): TokenId.ETH,
    # bnb tokens
    Address("0xbb4CdB9CBd36B01bD1cBaEBF2De08d9173bc095c"): TokenId.BNB,
    Address("0x4db5a66e937a9f4473fa95b1caf1d1e1d62e29ea"): TokenId.ETH,
    # linea tokens
    Address("0xe5D7C2a44FfDDf6b295A15c148167daaAf5Cf34f"): TokenId.ETH,
    # plasma tokens
    Address("0x6100e367285b01f48d07953803a2d8dca5d19873"): TokenId.XPL,
    Address("0x9895d81bb462a195b4922ed7de0e3acd007c32cb"): TokenId.ETH,
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
