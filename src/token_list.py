"""Utility code for fetching the allowed token list"""
import json

import requests

# pylint: disable=line-too-long
ALLOWED_TOKEN_LIST_URL = "https://raw.githubusercontent.com/gnosis/cow-dex-solver/main/data/token_list_for_buffer_trading.json"


def parse_token_list(token_list_json: str) -> list[str]:
    """Parses JSON-str token list as list of token addresses (as dune compatible bytes)"""
    try:
        token_list = json.loads(token_list_json)
    except json.JSONDecodeError:
        # TODO - raise properly here!
        print("Could not parse JSON data!")
        raise
    return [token["address"].lower() for token in token_list["tokens"]]


def fetch_trusted_tokens() -> list[str]:
    """Returns the list of trusted buffer tradable tokens"""
    response = requests.get(ALLOWED_TOKEN_LIST_URL)
    return parse_token_list(response.text)
