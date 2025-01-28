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
from src.config import AccountingConfig
from src.logger import set_log
from src.models.block_range import BlockRange
from src.utils.query_file import open_query

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
    def run_batch_data_query(
        cls, block_range: BlockRange, config: AccountingConfig
    ) -> DataFrame:
        """
        Fetches and validates Batch Data DataFrame as concatenation from Prod and Staging DB
        """
        load_dotenv()
        batch_data_query_prod = (
            open_query("orderbook/prod_batch_rewards.sql")
            .replace("{{start_block}}", str(block_range.block_from))
            .replace("{{end_block}}", str(block_range.block_to))
            .replace(
                "{{EPSILON_LOWER}}", str(config.reward_config.batch_reward_cap_lower)
            )
            .replace(
                "{{EPSILON_UPPER}}", str(config.reward_config.batch_reward_cap_upper)
            )
            .replace("{{results}}", "dune_sync_batch_data_table")
        )
        batch_data_query_barn = (
            open_query("orderbook/barn_batch_rewards.sql")
            .replace("{{start_block}}", str(block_range.block_from))
            .replace("{{end_block}}", str(block_range.block_to))
            .replace(
                "{{EPSILON_LOWER}}", str(config.reward_config.batch_reward_cap_lower)
            )
            .replace(
                "{{EPSILON_UPPER}}", str(config.reward_config.batch_reward_cap_upper)
            )
            .replace("{{results}}", "dune_sync_batch_data_table")
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
    def get_batch_data(
        cls, block_range: BlockRange, config: AccountingConfig
    ) -> DataFrame:
        """
        Decomposes the block range into buckets of X blocks each,
        where X depends on the chain, so as to ensure the
        batch data query runs fast enough.
        At the end, it concatenates everything into one data frame
        """
        start = block_range.block_from
        end = block_range.block_to
        bucket_size = config.data_processing_config.bucket_size
        res = []
        while start <= end:
            size = min(end - start + 1, bucket_size)
            log.info(f"About to process block range ({start}, {start + size - 1})")
            res.append(
                cls.run_batch_data_query(
                    BlockRange(block_from=start, block_to=start + size - 1),
                    config=config,
                )
            )
            start = start + size
        return pd.concat(res)

    @classmethod
    def run_order_data_query(
        cls, block_range: BlockRange, blockchain: str
    ) -> DataFrame:
        """
        Fetches and validates Order Data DataFrame as concatenation from Prod and Staging DB
        """
        barn_auction_prices_corrections_str = (
            open_query("orderbook/auction_prices_corrections.sql")
            .replace("{{blockchain}}", blockchain)
            .replace("{{environment}}", "barn")
        )
        prod_auction_prices_corrections_str = (
            open_query("orderbook/auction_prices_corrections.sql")
            .replace("{{blockchain}}", blockchain)
            .replace("{{environment}}", "prod")
        )
        cow_reward_query_prod = (
            open_query("orderbook/order_data.sql")
            .replace("{{start_block}}", str(block_range.block_from))
            .replace("{{end_block}}", str(block_range.block_to))
            .replace("{{env}}", "prod")
            .replace(
                "{{auction_prices_corrections}}", prod_auction_prices_corrections_str
            )
        )
        cow_reward_query_barn = (
            open_query("orderbook/order_data.sql")
            .replace("{{start_block}}", str(block_range.block_from))
            .replace("{{end_block}}", str(block_range.block_to))
            .replace("{{env}}", "barn")
            .replace(
                "{{auction_prices_corrections}}", barn_auction_prices_corrections_str
            )
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
    def get_order_data(
        cls, block_range: BlockRange, config: AccountingConfig
    ) -> DataFrame:
        """
        Decomposes the block range into buckets of 10k blocks each,
        so as to ensure the batch data query runs fast enough.
        At the end, it concatenates everything into one data frame
        """
        load_dotenv()
        start = block_range.block_from
        end = block_range.block_to
        bucket_size = config.data_processing_config.bucket_size
        res = []
        while start < end:
            size = min(end - start + 1, bucket_size)
            log.info(f"About to process block range ({start}, {start + size - 1})")
            res.append(
                cls.run_order_data_query(
                    BlockRange(
                        block_from=start,
                        block_to=start + size - 1,
                    ),
                    config.dune_config.dune_blockchain,
                )
            )
            start = start + size
        return pd.concat(res)

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
