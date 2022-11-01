"""Utility code for fetching the allowed token list"""
import json

import requests

from src.update.token_list import update_token_list
from src.utils.script_args import generic_script_init

ALLOWED_TOKEN_LIST_URL = "https://files.cow.fi/token_list.json"


def parse_token_list(token_list_json: str) -> list[str]:
    """Parses JSON-str token list as list of token addresses (as dune compatible bytes)"""
    try:
        token_list = json.loads(token_list_json)
    except json.JSONDecodeError:
        # TODO - raise properly here!
        print("Could not parse JSON data!")
        raise
    return [
        f"('\\{token['address'].lower()[1:]}'::bytea)"
        for token in token_list["tokens"]
        if token["chainId"] == 1
    ]


def fetch_trusted_tokens() -> list[str]:
    """Returns the list of trusted buffer tradable tokens"""
    response = requests.get(ALLOWED_TOKEN_LIST_URL)
    return parse_token_list(response.text)


if __name__ == "__main__":
    dune_connection = generic_script_init(description="Update Token List").dune
    update_token_list(dune_connection, fetch_trusted_tokens())
