"""Fetching Per Order Rewards from Production and Staging Database"""
import pandas as pd
from duneapi.util import open_query
from pandas import DataFrame

from src.pg_client import pg_engine, OrderbookEnv


def get_orderbook_rewards(start_block: str, end_block: str) -> DataFrame:
    """Fetches and validates Orderbook Reward DataFrame as concatenation from Prod and Staging DB"""
    cow_reward_query = (
        open_query("./queries/cow_rewards.sql")
        .replace("{{start_block}}", start_block)
        .replace("{{end_block}}", end_block)
    )

    # Need to fetch results from both order-books (prod and barn)
    prod_df: DataFrame = pd.read_sql(
        sql=cow_reward_query, con=pg_engine(OrderbookEnv.PROD)
    )
    print(f"got {prod_df} from production DB")
    barn_df: DataFrame = pd.read_sql(
        sql=cow_reward_query, con=pg_engine(OrderbookEnv.BARN)
    )
    print(f"got {barn_df} from staging DB")
    # Solvers do not appear in both environments!
    assert set(prod_df.solver).isdisjoint(set(barn_df.solver)), "receiver overlap!"
    return pd.concat([prod_df, barn_df])
