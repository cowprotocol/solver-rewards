"""Basic client for connecting to postgres database with login credentials"""
import os
from enum import Enum

from dotenv import load_dotenv
from sqlalchemy import create_engine, engine


class OrderbookEnv(Enum):
    """
    Enum for distinguishing between CoW Protocol's staging and production environment
    """

    BARN = "BARN"
    PROD = "PROD"

    def __str__(self) -> str:
        return str(self.value)


def pg_engine(db_env: OrderbookEnv) -> engine:
    """Returns a connection to postgres database"""
    load_dotenv()
    host = os.environ[f"{db_env}_ORDERBOOK_HOST"]
    port = os.environ[f"{db_env}_ORDERBOOK_PORT"]
    database = os.environ[f"{db_env}_ORDERBOOK_DB"]
    user = os.environ[f"{db_env}_ORDERBOOK_USER"]
    password = os.environ[f"{db_env}_ORDERBOOK_PASSWORD"]
    db_string = f"postgresql+psycopg2://{user}:{password}@{host}:{port}/{database}"
    return create_engine(db_string)
