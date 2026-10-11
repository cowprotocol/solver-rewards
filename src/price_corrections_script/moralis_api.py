"""Minimal Moralis Data API client for historical token prices."""

from __future__ import annotations

import time
from dataclasses import dataclass
from datetime import datetime, timezone
from typing import Any

import requests

from src.config import Network

BASE_URL = "https://deep-index.moralis.io/api/v2.2"
# Cloudflare in front of Moralis rejects the default python User-Agent (error 1010).
USER_AGENT = "Mozilla/5.0 (compatible; cow-solver-rewards/price-corrections)"
RETRY_STATUS = {429, 500, 502, 503, 504}


@dataclass(frozen=True)
class ChainConfig:
    """How a chain is named on Dune, in our output and on Moralis."""

    dune_name: str
    network: Network
    moralis_chain: str  # hex chain id, accepted by every Moralis endpoint
    wrapped_native: str  # lower-case address, as used in query 8766284


CHAINS: dict[str, ChainConfig] = {
    c.dune_name: c
    for c in [
        ChainConfig(
            "ethereum",
            Network.MAINNET,
            "0x1",
            "0xc02aaa39b223fe8d0a0e5c4f27ead9083c756cc2",
        ),
        ChainConfig(
            "gnosis",
            Network.GNOSIS,
            "0x64",
            "0xe91d153e0b41518a2ce8dd3d7944fa863463a97d",
        ),
        ChainConfig(
            "arbitrum",
            Network.ARBITRUM_ONE,
            "0xa4b1",
            "0x82af49447d8a07e3bd95bd0d56f35241523fbab1",
        ),
        ChainConfig(
            "base", Network.BASE, "0x2105", "0x4200000000000000000000000000000000000006"
        ),
        ChainConfig(
            "avalanche_c",
            Network.AVALANCHE,
            "0xa86a",
            "0xb31f66aa3c1e785363f0875a1b74e27b85fd66c7",
        ),
        ChainConfig(
            "polygon",
            Network.POLYGON,
            "0x89",
            "0x0d500b1d8e8ef31e21c99d1db9a6444d3adf1270",
        ),
        ChainConfig(
            "bnb", Network.BNB, "0x38", "0xbb4cdb9cbd36b01bd1cbaebf2de08d9173bc095c"
        ),
        ChainConfig(
            "linea",
            Network.LINEA,
            "0xe708",
            "0xe5d7c2a44ffddf6b295a15c148167daaaf5cf34f",
        ),
        ChainConfig(
            "plasma",
            Network.PLASMA,
            "0x2611",  # 9745
            "0x6100e367285b01f48d07953803a2d8dca5d19873",
        ),
        ChainConfig(
            "ink",
            Network.INK,
            "0xdef1",  # 57073
            "0x4200000000000000000000000000000000000006",
        ),
    ]
}


@dataclass(frozen=True)
class MoralisPrice:
    """Price of one atom of a token, as reported by Moralis at some block."""

    usd_per_atom: float | None  # None when Moralis gives no USD price
    native_per_atom: float  # atoms of the native token per atom of the token
    symbol: str
    exchange: str
    possible_spam: bool


def parse_price(response: dict[str, Any], wrapped_native: str) -> MoralisPrice:
    """Convert a Moralis /erc20/{address}/price response into per-atom prices.

    `nativePrice.value` is denominated in atoms of the native token per one
    *whole* token, so it is divided by 10^tokenDecimals to get a per-atom price.
    """
    native = response.get("nativePrice") or {}
    if native.get("value") in (None, ""):  # an explicit 0 is a valid price
        raise ValueError("Moralis response has no nativePrice")
    native_address = str(native.get("address") or "").lower()
    if native_address and native_address != wrapped_native:
        raise ValueError(
            f"nativePrice is quoted in {native.get('symbol')} ({native_address}), "
            f"expected {wrapped_native}"
        )
    token_decimals = int(response["tokenDecimals"])
    native_decimals = int(native.get("decimals", 18))
    atoms_per_whole_token = 10.0**token_decimals
    native_atoms_per_whole_token = float(native["value"]) * 10.0 ** (
        18 - native_decimals
    )
    usd_price = response.get("usdPrice")
    return MoralisPrice(
        usd_per_atom=(
            None if usd_price is None else float(usd_price) / atoms_per_whole_token
        ),
        native_per_atom=native_atoms_per_whole_token / atoms_per_whole_token,
        symbol=str(response.get("tokenSymbol") or ""),
        exchange=str(response.get("exchangeName") or ""),
        possible_spam=bool(response.get("possibleSpam")),
    )


class MoralisClient:
    """Rate limited, caching client for the two endpoints we need."""

    def __init__(
        self, api_key: str, min_interval: float = 0.03, max_retries: int = 5
    ) -> None:
        self.session = requests.Session()
        self.session.headers.update(
            {
                "X-API-Key": api_key,
                "Accept": "application/json",
                "User-Agent": USER_AGENT,
            }
        )
        # min_interval is the min gap in seconds between two requests
        # this is used to avoid rate limiting
        self.min_interval = min_interval
        self.max_retries = max_retries
        self._last_call = 0.0
        self._blocks: dict[tuple[str, int], int] = {}
        self._prices: dict[tuple[str, str, int], dict[str, Any]] = {}

    def _get(self, path: str, params: dict[str, Any]) -> dict[str, Any]:
        delay = 1.0
        for attempt in range(self.max_retries):
            wait = self.min_interval - (time.monotonic() - self._last_call)
            if wait > 0:
                time.sleep(wait)
            self._last_call = time.monotonic()
            try:
                resp = self.session.get(f"{BASE_URL}{path}", params=params, timeout=30)
            except requests.RequestException as err:
                if attempt == self.max_retries - 1:
                    raise RuntimeError(f"Network error for {path}: {err}") from err
            else:
                if resp.ok:
                    data: dict[str, Any] = resp.json()
                    return data
                if (
                    resp.status_code not in RETRY_STATUS
                    or attempt == self.max_retries - 1
                ):
                    raise RuntimeError(
                        f"HTTP {resp.status_code} for {path} {params}: {resp.text[:300]}"
                    )
            time.sleep(delay)
            delay *= 2
        raise RuntimeError(f"Gave up on {path}")

    def price_at(
        self, chain: ChainConfig, token: str, block_number: int
    ) -> MoralisPrice:
        """Price of `token` at `block_number`."""
        key = (chain.moralis_chain, token, block_number)
        if key not in self._prices:
            self._prices[key] = self._get(
                f"/erc20/{token}/price",
                {"chain": chain.moralis_chain, "to_block": block_number},
            )
        return parse_price(self._prices[key], chain.wrapped_native)
