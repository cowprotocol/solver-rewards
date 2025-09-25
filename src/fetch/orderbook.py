# pylint: disable=duplicate-code
"""Basic client for connecting to postgres database with login credentials"""

from __future__ import annotations

import os
from dataclasses import dataclass
from enum import Enum
from typing import Optional

import pandas as pd
from dotenv import load_dotenv
from pandas import DataFrame, read_sql_table
from sqlalchemy import create_engine
from sqlalchemy.engine import Engine
from src.logger import set_log

log = set_log(__name__)

MAX_PROCESSING_DELAY = 10


class OrderbookEnv(Enum):
    """
    Enum for distinguishing between CoW Protocol's staging and production environment
    """

    BARN = "BARN"
    PROD = "PROD"
    ANALYTICS = "ANALYTICS"

    def __str__(self) -> str:
        return str(self.value)


@dataclass
class OrderbookFetcher:
    """
    A pair of Dataframes primarily intended to store query results
    from production and staging orderbook databases
    """

    @staticmethod
    def pg_engine(db_env: OrderbookEnv) -> Engine:
        """Returns a connection to postgres database"""
        load_dotenv()
        if db_env == OrderbookEnv.ANALYTICS:
            db_url = os.environ["ANALYTICS_DB_URL"]
        else:
            db_url = os.environ[f"{db_env}_DB_URL"]

        return create_engine(
            f"postgresql+psycopg2://{db_url}",
            pool_pre_ping=True,
            connect_args={
                "keepalives": 1,
                "keepalives_idle": 30,
                "keepalives_interval": 10,
                "keepalives_count": 5,
            },
        )

    @classmethod
    def _read_query_for_env(
        cls, query: str, env: OrderbookEnv, data_types: Optional[dict[str, str]] = None
    ) -> DataFrame:
        return pd.read_sql_query(query, con=cls.pg_engine(env), dtype=data_types)

    @classmethod
    def _query_both_dbs(
        cls,
        query_prod: str,
        query_barn: str,
        data_types: Optional[dict[str, str]] = None,
    ) -> tuple[DataFrame, DataFrame]:
        barn = cls._read_query_for_env(query_barn, OrderbookEnv.BARN, data_types)
        prod = cls._read_query_for_env(query_prod, OrderbookEnv.PROD, data_types)
        return barn, prod

    @classmethod
    def write_data(
        cls,
        type_of_data: str,
        new_data: DataFrame,
        table_name: str,
        recreate_table: bool = False,
    ) -> None:
        """Write new data into database table.
        Data is upserted: it is inserted if possible (i.e. it does not yet exist) and updated
        otherwise."""
        if recreate_table:
            log.info(f"(Re)creating table {table_name}.")
            data = new_data
        else:
            # set index for upserting data depending on type of data
            match type_of_data:
                case "batch":
                    index_cols = ["environment", "auction_id"]
                case "order":
                    index_cols = ["environment", "auction_id", "order_uid"]
                case _:
                    raise ValueError(f"Unknown type {type_of_data}")

            # set index of new data
            new_data = new_data.set_index(index_cols)
            # try getting table data from database, just use new_data if table is not available
            try:
                data = read_sql_table(
                    table_name,
                    cls.pg_engine(OrderbookEnv.ANALYTICS),
                    index_col=index_cols,
                )
                # upsert data (insert if possible, otherwise update)
                log.info(f"Upserting into table {table_name}.")
                data = pd.concat([data[~data.index.isin(new_data.index)], new_data])
            except ValueError:  # this catches the case of a missing table
                data = new_data
                log.info(f"Creating new table {table_name}.")
        data = data.reset_index()
        data.to_sql(
            table_name,
            cls.pg_engine(OrderbookEnv.ANALYTICS),
            if_exists="replace",
            index=False,
        )
