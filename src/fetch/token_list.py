"""
Standalone script for fetching the trusted token
list and pushing the data to a dune user generated view.
"""
from __future__ import annotations

import json
import logging.config

import requests

from src.constants import LOG_CONFIG_FILE

log = logging.getLogger(__name__)
logging.config.fileConfig(
    fname=LOG_CONFIG_FILE.absolute(), disable_existing_loggers=False
)

ALLOWED_TOKEN_LIST_URL = "https://files.cow.fi/token_list.json"


def parse_token_list(token_list_json: str) -> list[str]:
    """
    Parses JSON-str token list as list of token dune-compatible VALUES list of EVM addresses
    See PoC Query for example formatting: https://dune.com/queries/1547103
    """
    try:
        token_list = json.loads(token_list_json)
    except json.JSONDecodeError:
        # TODO - raise properly here!
        print("Could not parse JSON data!")
        raise
    return [
        f"('{t['address'].replace('0x', '')}')"
        for t in token_list["tokens"]
        if t["chainId"] == 1
    ]


def get_trusted_tokens() -> list[str]:
    """Returns the list of trusted buffer tradable tokens"""
    response = requests.get(ALLOWED_TOKEN_LIST_URL, timeout=10)
    return parse_token_list(response.text)
