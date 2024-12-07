"""Basic client for connecting to postgres database with login credentials"""

from __future__ import annotations

import os
from dataclasses import dataclass
from enum import Enum
from typing import Optional

import pandas as pd
from dotenv import load_dotenv
from pandas import DataFrame
from sqlalchemy import create_engine
from sqlalchemy.engine import Engine

from src.logger import set_log
from src.models.block_range import BlockRange
from src.utils.query_file import open_query
from src.dbt.common import node_suffix

log = set_log(__name__)

MAX_PROCESSING_DELAY = 10
BUCKET_SIZE = {"mainnet": 10000, "xdai": 30000, "arbitrum-one": 1000000}


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
    def _pg_engine(db_env: OrderbookEnv) -> Engine:
        """Returns a connection to postgres database"""
        load_dotenv()
        if db_env == OrderbookEnv.ANALYTICS:
            db_url = os.environ["ANALYTICS_DB_URL"]
            db_string = f"postgresql+psycopg2://{db_url}"
            return create_engine(db_string)

        db_url = os.environ[f"{db_env}_DB_URL"]
        db_string = f"postgresql+psycopg2://{db_url}"
        return create_engine(db_string)

    @classmethod
    def _read_query_for_env(
        cls, query: str, env: OrderbookEnv, data_types: Optional[dict[str, str]] = None
    ) -> DataFrame:
        return pd.read_sql_query(query, con=cls._pg_engine(env), dtype=data_types)

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
    def get_order_rewards(cls, block_range: BlockRange) -> DataFrame:
        """
        Fetches and validates Order Reward DataFrame as concatenation from Prod and Staging DB
        """
        cow_reward_query_prod = (
            open_query("orderbook/prod_order_rewards.sql")
            .replace("{{start_block}}", str(block_range.block_from))
            .replace("{{end_block}}", str(block_range.block_to))
        )
        cow_reward_query_barn = (
            open_query("orderbook/barn_order_rewards.sql")
            .replace("{{start_block}}", str(block_range.block_from))
            .replace("{{end_block}}", str(block_range.block_to))
        )
        data_types = {"block_number": "int64", "amount": "float64"}
        barn, prod = cls._query_both_dbs(
            cow_reward_query_prod, cow_reward_query_barn, data_types
        )

        # Warn if solver appear in both environments.
        if not set(prod.solver).isdisjoint(set(barn.solver)):
            log.warning(
                f"solver overlap in {block_range}: solvers "
                f"{set(prod.solver).intersection(set(barn.solver))} part of both prod and barn"
            )

        if not prod.empty and not barn.empty:
            return pd.concat([prod, barn])
        if not prod.empty:
            return prod.copy()
        if not barn.empty:
            return barn.copy()
        return pd.DataFrame()

    @classmethod
    def run_batch_data_query(cls, block_range: BlockRange) -> DataFrame:
        """
        Fetches and validates Batch data DataFrame as concatenation from Prod and Staging DB
        """
        load_dotenv()
        network = node_suffix(os.environ["NETWORK"])
        epsilon_upper = str(os.environ[f"EPSILON_UPPER_{network}"])
        epsilon_lower = str(os.environ[f"EPSILON_LOWER_{network}"])
        batch_data_query_prod = (
            open_query("orderbook/batch_data.sql")
            .replace("{{start_block}}", str(block_range.block_from))
            .replace("{{end_block}}", str(block_range.block_to))
            .replace(
                "{{EPSILON_LOWER}}", epsilon_lower
            )  # lower ETH cap for payment (in WEI)
            .replace(
                "{{EPSILON_UPPER}}", epsilon_upper
            )  # upper ETH cap for payment (in WEI)
            .replace("{{env}}", "prod")
        )
        batch_data_query_barn = (
            open_query("orderbook/batch_data.sql")
            .replace("{{start_block}}", str(block_range.block_from))
            .replace("{{end_block}}", str(block_range.block_to))
            .replace(
                "{{EPSILON_LOWER}}", epsilon_lower
            )  # lower ETH cap for payment (in WEI)
            .replace(
                "{{EPSILON_UPPER}}", epsilon_upper
            )  # upper ETH cap for payment (in WEI)
            .replace("{{env}}", "barn")
        )
        data_types = {
            # According to this: https://stackoverflow.com/a/11548224
            # capitalized int64 means `Optional<Integer>` and it appears to work.
            "block_number": "Int64",
            "block_deadline": "int64",
        }
        barn, prod = cls._query_both_dbs(
            batch_data_query_prod, batch_data_query_barn, data_types
        )

        # Warn if solver appear in both environments.
        if not set(prod.solver).isdisjoint(set(barn.solver)):
            log.warning(
                f"solver overlap in {block_range}: solvers "
                f"{set(prod.solver).intersection(set(barn.solver))} part of both prod and barn"
            )

        if not prod.empty and not barn.empty:
            return pd.concat([prod, barn])
        if not prod.empty:
            return prod.copy()
        if not barn.empty:
            return barn.copy()
        return pd.DataFrame()

    @classmethod
    def get_batch_data(cls, block_range: BlockRange) -> DataFrame:
        """
        Decomposes the block range into buckets of 10k blocks each,
        so as to ensure the batch data query runs fast enough.
        At the end, it concatenates everything into one data frame
        """
        load_dotenv()
        start = block_range.block_from
        end = block_range.block_to
        bucket_size = BUCKET_SIZE[os.environ.get("NETWORK", "mainnet")]
        res = []
        while start < end:
            size = min(end - start, bucket_size)
            log.info(f"About to process block range ({start}, {start + size})")
            res.append(
                cls.run_batch_data_query(
                    BlockRange(block_from=start, block_to=start + size)
                )
            )
            start = start + size
        return pd.concat(res)

    @classmethod
    def run_order_data_sql(cls, block_range: BlockRange) -> DataFrame:
        """
        Fetches and validates Order Reward DataFrame as concatenation from Prod and Staging DB
        """
        cow_reward_query_prod = (
            open_query("orderbook/order_data.sql")
            .replace("{{start_block}}", str(block_range.block_from))
            .replace("{{end_block}}", str(block_range.block_to))
            .replace("{{env}}", "prod")
        )
        cow_reward_query_barn = (
            open_query("orderbook/order_data.sql")
            .replace("{{start_block}}", str(block_range.block_from))
            .replace("{{end_block}}", str(block_range.block_to))
            .replace("{{env}}", "barn")
        )
        data_types = {"block_number": "int64", "amount": "float64"}
        barn, prod = cls._query_both_dbs(
            cow_reward_query_prod, cow_reward_query_barn, data_types
        )

        # Warn if solver appear in both environments.
        if not set(prod.solver).isdisjoint(set(barn.solver)):
            log.warning(
                f"solver overlap in {block_range}: solvers "
                f"{set(prod.solver).intersection(set(barn.solver))} part of both prod and barn"
            )

        if not prod.empty and not barn.empty:
            return pd.concat([prod, barn])
        if not prod.empty:
            return prod.copy()
        if not barn.empty:
            return barn.copy()
        return pd.DataFrame()

    @classmethod
    def get_order_data(cls, block_range: BlockRange) -> DataFrame:
        """
        Decomposes the block range into buckets of 10k blocks each,
        so as to ensure the batch data query runs fast enough.
        At the end, it concatenates everything into one data frame
        """
        load_dotenv()
        start = block_range.block_from
        end = block_range.block_to
        bucket_size = BUCKET_SIZE[os.environ.get("NETWORK", "mainnet")]
        res = []
        while start < end:
            size = min(end - start, bucket_size)
            log.info(f"About to process block range ({start}, {start + size})")
            res.append(
                cls.run_order_data_sql(
                    BlockRange(block_from=start, block_to=start + size)
                )
            )
            start = start + size
        return pd.concat(res)
