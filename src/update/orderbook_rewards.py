"""Pushes a new dune user generated view per Accounting Period
with name dune_user_generated.cow_rewards_{{PeriodHash}}
"""
from enum import Enum

from duneapi.api import DuneAPI
from duneapi.types import DuneQuery, Network
from duneapi.util import open_query
from pandas import DataFrame, Series

from src.models import AccountingPeriod
from src.utils.query_file import query_file


class RewardQuery(Enum):
    """different types of queries being pushed as user_generated_views"""

    AGGREGATE = "Aggregated"
    PER_ORDER = "Per Order"

    def dune_repr(self, df_row: Series) -> str:
        """
        This is the per row format for inserting entries in a table of VALUES
        Specific to a COW Reward Item
        """
        amount = df_row["amount"]
        if self == RewardQuery.AGGREGATE:
            return f"('{df_row['receiver'].lower()}', {df_row['num_trades']}, {amount})"
        if self == RewardQuery.PER_ORDER:
            solver, tx_hash = df_row["solver"].lower(), df_row["tx_hash"]
            safe = df_row["safe_liquidity"]
            safe = safe if safe is not None else "Null"
            # See https://dune.com/queries/1456810 for Null Test Demonstration
            return f"('{solver}', '{tx_hash}', {amount}, {safe})"

        raise ValueError(f"Invalid enum variant {self}")

    def to_dune_list(self, data: DataFrame) -> str:
        """Joins a list of VALUES into the format for postgres VALUES list for type"""
        return ",\n".join([self.dune_repr(row) for _, row in data.iterrows()])

    def query_file(self) -> str:
        """Returns the file containing the RAW SQL for Dune Query"""
        if self == RewardQuery.AGGREGATE:
            return query_file("user_generated_rewards.sql")
        if self == RewardQuery.PER_ORDER:
            return query_file("user_generated_per_order_rewards.sql")

        raise ValueError(f"Invalid enum variant {self}")

    def dune_query(self, period: AccountingPeriod, data: DataFrame) -> str:
        """Returns query associated with the upsert of orderbook cow reward data"""
        return (
            open_query(self.query_file())
            .replace("{{PeriodHash}}", str(hash(period)))
            .replace("{{SolverRewards}}", self.to_dune_list(data))
        )

    def view_name(self) -> str:
        """Returns Name of the user generated view Dune table"""
        if self == RewardQuery.AGGREGATE:
            return "cow_rewards"
        if self == RewardQuery.PER_ORDER:
            return "cow_per_order_rewards"

        raise ValueError(f"Invalid enum variant {self}")


def push_user_generated_view(
    dune: DuneAPI, period: AccountingPeriod, data: DataFrame, data_type: RewardQuery
) -> None:
    """
    Upsert SQL query constructing  a user generated view to Dune V1
    """
    results = dune.fetch(
        query=DuneQuery.from_environment(
            raw_sql=data_type.dune_query(period, data),
            name=f"Orderbook {data_type} Rewards",
            network=Network.MAINNET,
        )
    )
    assert len(data) == len(results)
    print(f"Pushed User Generated view {data_type.view_name()}_{hash(period)}")
