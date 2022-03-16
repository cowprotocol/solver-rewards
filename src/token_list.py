"""Utility code for fetching the allowed token list"""
import json
import requests

# pylint: disable=line-too-long
ALLOWED_TOKEN_LIST_URL = "https://raw.githubusercontent.com/gnosis/cow-dex-solver/main/data/token_list_for_buffer_trading.json"


def get_trusted_tokens(token_list_json: str) -> list[str]:
    """Get list of trusted token IDs from JSON-str."""
    try:
        token_list = json.loads(token_list_json)
    except json.JSONDecodeError:
        print("Could not parse JSON data!")
        raise
    return [token["address"].lower() for token in token_list["tokens"]]


def get_trusted_tokens_from_url(url: str) -> list[str]:
    """Returns the list of trusted buffer tradable tokens"""
    response = requests.get(url)
    return get_trusted_tokens(response.text)
