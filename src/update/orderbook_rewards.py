"""Pushes a new dune user generated view per Accounting Period
with name dune_user_generated.cow_rewards_{{PeriodHash}}
"""
from duneapi.api import DuneAPI
from duneapi.types import DuneQuery, Network
from duneapi.util import open_query
from pandas import DataFrame, Series

from src.models import AccountingPeriod


def dune_repr(df_row: Series) -> str:
    """
    This is the per row format for inserting entries in a table of VALUES
    Specific to a COW Reward Item
    """
    return (
        f"('{df_row['receiver'].lower()}', {df_row['num_trades']}, {df_row['amount']})"
    )


def rewards_df_to_dune_list(data: DataFrame) -> str:
    """Joins a list of VALUES into the format for postgres VALUES list"""
    return ",\n".join([dune_repr(row) for _, row in data.iterrows()])


def orderbook_rewards_query(period: AccountingPeriod, data: DataFrame) -> str:
    """Returns query associated with the upsert of orderbook cow reward data"""
    return (
        open_query("./queries/user_generated_rewards.sql")
        .replace("{{PeriodHash}}", str(hash(period)))
        .replace("{{SolverRewards}}", rewards_df_to_dune_list(data))
    )


def push_user_generated_view(
    dune: DuneAPI, period: AccountingPeriod, data: DataFrame
) -> None:
    """
    Upsert SQL query constructing  a user generated view to Dune V1
    """
    results = dune.fetch(
        query=DuneQuery.from_environment(
            raw_sql=orderbook_rewards_query(period, data),
            name="Orderbook Rewards",
            network=Network.MAINNET,
        )
    )
    assert len(data) == len(results)
    print(f"Pushed User Generated view cow_rewards_{hash(period)}")
