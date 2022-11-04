"""Basic client for connecting to postgres database with login credentials"""
from __future__ import annotations

import os
from dataclasses import dataclass
from enum import Enum

import pandas as pd
from dotenv import load_dotenv
from duneapi.util import open_query
from pandas import DataFrame
from sqlalchemy import create_engine
from sqlalchemy.engine import Engine

from src.utils.query_file import query_file


class OrderbookEnv(Enum):
    """
    Enum for distinguishing between CoW Protocol's staging and production environment
    """

    BARN = "BARN"
    PROD = "PROD"

    def __str__(self) -> str:
        return str(self.value)


@dataclass
class DualEnvDataframe:
    """
    A pair of Dataframes primarily intended to store query results
    from production and staging orderbook databases
    """

    barn: DataFrame
    prod: DataFrame

    @staticmethod
    def _pg_engine(db_env: OrderbookEnv) -> Engine:
        """Returns a connection to postgres database"""
        load_dotenv()
        host = os.environ[f"{db_env}_ORDERBOOK_HOST"]
        port = os.environ[f"{db_env}_ORDERBOOK_PORT"]
        database = os.environ[f"{db_env}_ORDERBOOK_DB"]
        user = os.environ[f"{db_env}_ORDERBOOK_USER"]
        password = os.environ[f"{db_env}_ORDERBOOK_PASSWORD"]
        db_string = f"postgresql+psycopg2://{user}:{password}@{host}:{port}/{database}"
        return create_engine(db_string)

    @classmethod
    def from_query(cls, query: str) -> DualEnvDataframe:
        """Fetch results of DB query on both prod and barn and returns the results as a pair"""
        return cls(
            barn=pd.read_sql(sql=query, con=cls._pg_engine(OrderbookEnv.PROD)),
            prod=pd.read_sql(sql=query, con=cls._pg_engine(OrderbookEnv.BARN)),
        )

    def merge(self) -> DataFrame:
        """Merges prod and barn dataframes via concatenation"""
        # TODO - verify generic disjointness here.
        return pd.concat([self.prod, self.barn])

    @classmethod
    def get_orderbook_rewards(cls, start_block: str, end_block: str) -> DataFrame:
        """
        Fetches and validates Orderbook Reward DataFrame as concatenation from Prod and Staging DB
        """
        cow_reward_query = (
            open_query(query_file("orderbook/order_rewards.sql"))
            .replace("{{start_block}}", start_block)
            .replace("{{end_block}}", end_block)
        )
        dual_df = cls.from_query(cow_reward_query)

        # Solvers do not appear in both environments!
        # TODO - move this assertion into merge:
        #  https://github.com/cowprotocol/solver-rewards/issues/125
        assert set(dual_df.prod.solver).isdisjoint(
            set(dual_df.barn.solver)
        ), "solver overlap!"
        return dual_df.merge()


def pg_hex2bytea(hex_address: str) -> str:
    """
    transforms hex string (beginning with 0x) to dune
    compatible bytea by replacing `0x` with `\\x`.
    """
    return hex_address.replace("0x", "\\x")
