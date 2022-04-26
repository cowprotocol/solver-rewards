"""Tool fetching Trusted Token list and pushing the data to a dune user generated view."""
from __future__ import annotations

import logging.config

from duneapi.api import DuneAPI
from duneapi.types import DuneQuery, Network
from duneapi.util import open_query

log = logging.getLogger(__name__)
logging.config.fileConfig(fname="logging.conf", disable_existing_loggers=False)


def update_token_list(dune: DuneAPI, token_list: list[str]) -> list[dict[str, str]]:
    """Fetches current trusted token list and builds a user generated view from it"""
    raw_sql = open_query("./queries/token_list.sql").replace(
        "'{{TokenList}}'",
        ",\n             ".join(token_list),
    )
    query = DuneQuery.from_environment(raw_sql=raw_sql, network=Network.MAINNET)
    # We return the fetched list (for testing), but we really only care that the data has been pushed and updated
    return dune.fetch(query)
