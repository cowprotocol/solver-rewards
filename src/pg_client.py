"""Basic client for connecting to postgres database with login credentials"""
from __future__ import annotations


import pandas as pd
from pandas import DataFrame
from sqlalchemy import create_engine
from sqlalchemy.engine import Engine

from src.utils.query_file import open_query


class MultiInstanceDBFetcher:
    """
    Allows identical query execution on multiple db instances (merging results).
    Currently very specific to the CoW Protocol Orderbook DB.
    """

    def __init__(self, db_urls: list[str]):
        self.connections = [
            create_engine(f"postgresql+psycopg2://{url}") for url in db_urls
        ]

    @classmethod
    def exec_query(cls, query: str, engine: Engine) -> DataFrame:
        """Executes query on DB engine"""
        return pd.read_sql(sql=query, con=engine)

    def get_solver_rewards(self, start_block: str, end_block: str) -> DataFrame:
        """
        Returns aggregated solver rewards for accounting period defined by block range
        """
        batch_reward_query = (
            open_query("orderbook/batch_rewards.sql")
            .replace("{{start_block}}", start_block)
            .replace("{{end_block}}", end_block)
            .replace("{{EPSILON}}", "10000000000000000")
        )
        results = [
            self.exec_query(query=batch_reward_query, engine=engine)
            for engine in self.connections
        ]

        return pd.concat(results)

    def get_quote_rewards(self, start_block: str, end_block: str) -> DataFrame:
        """Returns aggregated solver quote rewards for block range"""
        quote_reward_query = (
            open_query("orderbook/quote_rewards.sql")
            .replace("{{start_block}}", start_block)
            .replace("{{end_block}}", end_block)
        )
        results = [
            self.exec_query(query=quote_reward_query, engine=engine)
            for engine in self.connections
        ]

        return pd.concat(results)

    def get_protocol_fees(self, start_block: str, end_block: str) -> DataFrame:
        """Returns aggregated solver protocol fees for block range"""
        protocol_fee_query = (
            open_query("orderbook/protocol_fees.sql")
            .replace("{{start_block}}", start_block)
            .replace("{{end_block}}", end_block)
        )
        results = [
            self.exec_query(query=protocol_fee_query, engine=engine)
            for engine in self.connections
        ]

        return pd.concat(results)


def pg_hex2bytea(hex_address: str) -> str:
    """
    transforms hex string (beginning with 0x) to dune
    compatible bytea by replacing `0x` with `\\x`.
    """
    return hex_address.replace("0x", "\\x")
