"""Basic client for connecting to postgres database with login credentials"""

from __future__ import annotations


import pandas as pd
from pandas import DataFrame
from sqlalchemy import create_engine
from sqlalchemy.engine import Engine

from src.logger import set_log
from src.utils.query_file import open_query

log = set_log(__name__)


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
        batch_reward_query_prod = (
            open_query("orderbook/prod_batch_rewards.sql")
            .replace("{{start_block}}", start_block)
            .replace("{{end_block}}", end_block)
            .replace("{{EPSILON_LOWER}}", "10000000000000000")
            .replace("{{EPSILON_UPPER}}", "12000000000000000")
        )
        batch_reward_query_barn = (
            open_query("orderbook/barn_batch_rewards.sql")
            .replace("{{start_block}}", start_block)
            .replace("{{end_block}}", end_block)
            .replace("{{EPSILON_LOWER}}", "10000000000000000")
            .replace("{{EPSILON_UPPER}}", "12000000000000000")
        )
        results = []

        # Here, we use the convention that we run the prod query for the first connection
        # and the barn query to all other connections
        results.append(
            self.exec_query(query=batch_reward_query_prod, engine=self.connections[0])
        )
        for engine in self.connections[1:]:
            results.append(
                self.exec_query(query=batch_reward_query_barn, engine=engine)
            )

        results_df = pd.concat(results)

        # warn and merge in case of solvers in both environments
        if not results_df["solver"].is_unique:
            duplicated_entries = results_df[results_df["solver"].duplicated(keep=False)]
            log.warning(
                f"Solvers found in both environments:\n {duplicated_entries}.\n Merging results."
            )

            def merge_lists(series):
                merged = []
                for lst in series:
                    if lst is not None:
                        merged.extend(lst)
                return merged if merged else None

            results_df = (
                results_df.groupby("solver")
                .agg(
                    {
                        "primary_reward_eth": "sum",
                        "protocol_fee_eth": "sum",
                        "network_fee_eth": "sum",
                        # there can be duplicate entries in partner_list now
                        "partner_list": merge_lists,
                        "partner_fee_eth": merge_lists,
                    }
                )
                .reset_index()
            )

        return results_df

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
        results_df = pd.concat(results)

        # warn and merge in case of solvers in both environments
        if not results_df["solver"].is_unique:
            duplicated_entries = results_df[results_df["solver"].duplicated(keep=False)]
            log.warning(
                f"Solvers found in both environments:\n {duplicated_entries}.\n Merging results."
            )
            results_df = (
                results_df.groupby("solver").agg({"num_quotes": "sum"}).reset_index()
            )

        return results_df


def pg_hex2bytea(hex_address: str) -> str:
    """
    transforms hex string (beginning with 0x) to dune
    compatible bytea by replacing `0x` with `\\x`.
    """
    return hex_address.replace("0x", "\\x")
