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
