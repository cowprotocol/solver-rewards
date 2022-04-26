"""A standalone script for fetching Solver Slippage for Accounting Period"""
from __future__ import annotations

import logging.config

from duneapi.api import DuneAPI
from duneapi.types import DuneQuery, Network
from duneapi.util import open_query

from src.token_list import fetch_trusted_tokens

log = logging.getLogger(__name__)
logging.config.fileConfig(fname="logging.conf", disable_existing_loggers=False)


def update_token_list(dune: DuneAPI) -> None:
    """Fetches current trusted token list and builds a user generated view from it"""
    token_list = fetch_trusted_tokens()
    raw_sql = open_query("./queries/token_list.sql").replace(
        "'{{TokenList}}'",
        ",\n             ".join(token_list),
    )
    query = DuneQuery.from_environment(raw_sql=raw_sql, network=Network.MAINNET)
    dune.fetch(query)
