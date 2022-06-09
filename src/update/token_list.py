"""
Standalone script for fetching the trusted token
list and pushing the data to a dune user generated view.
"""
from __future__ import annotations

import logging.config

from duneapi.api import DuneAPI
from duneapi.types import DuneQuery, Network
from duneapi.util import open_query

from src.token_list import fetch_trusted_tokens
from src.utils.script_args import generic_script_init

log = logging.getLogger(__name__)
logging.config.fileConfig(fname="logging.conf", disable_existing_loggers=False)


def update_token_list(dune: DuneAPI, token_list: list[str]) -> list[dict[str, str]]:
    """Fetches current trusted token list and builds a user generated view from it"""
    if not token_list:
        raise ValueError("Can't update and empty token list")
    raw_sql = open_query("./queries/token_list.sql").replace(
        "'{{TokenList}}'",
        ",\n             ".join(token_list),
    )
    query = DuneQuery.from_environment(
        raw_sql=raw_sql, name="Updated Token List", network=Network.MAINNET
    )
    # We return the fetched list (for testing),
    # but we really only care that the data has been pushed and updated
    results = dune.fetch(query)
    # This assertion ensures that the token list was successfully updated.
    assert len(results) == len(token_list), "Query Failed to push token list"
    return results


if __name__ == "__main__":
    dune_connection, _ = generic_script_init(description="Update Token List")
    update_token_list(dune_connection, fetch_trusted_tokens())
