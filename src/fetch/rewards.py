"""Functionality for computing solver rewards

The only function used in other parts of the code is `compute_solver_rewards` for generating
aggregate reward information per solver."""

from pandas import DataFrame, Series
from src.fetch.prices import TokenConversion

EPSILON_UPPER = 12000000000000000
EPSILON_LOWER = 10000000000000000
PERIOD_BUDGET_COW = 250000 * 10**18
CONSISTENCY_REWARD_CAP_ETH = 6 * 10**18
QUOTE_REWARD_COW = 6 * 10**18
QUOTE_REWARD_CAP_ETH = 6 * 10**14


def compute_solver_rewards(
    batch_data_df: DataFrame, trade_data_df: DataFrame, converter: TokenConversion
) -> DataFrame:
    """Compute solver rewards
    The input dataframes `batch_data_df` and `trade_data_df` containd data on batches and
    trades, respectively. It requires TokenConversion to convert betwenn ETH and COW.
    The function creates a new dataframe with information on primary, secondary, and quote rewards.
    """
    # primary reward
    primary_rewards_df = compute_primary_rewards(batch_data_df, converter)

    # secondary rewards
    secondary_rewards_df = compute_secondary_rewards_df(
        batch_data_df, primary_rewards_df, converter
    )

    # quote rewards
    quote_rewards_df = compute_quote_rewards(trade_data_df, converter)

    # merge different rewards
    solver_rewards_df = (
        primary_rewards_df.merge(secondary_rewards_df, on="solver", how="outer")
    ).merge(quote_rewards_df, on="solver", how="outer")

    return solver_rewards_df


def compute_primary_rewards(
    batch_data_df: DataFrame, converter: TokenConversion
) -> DataFrame:
    """Compute primary rewards from batch data"""
    primary_rewards_df = (
        batch_data_df.apply(compute_primary_reward_datum, axis=1, result_type="expand")
        .rename(columns={0: "solver", 1: "primary_reward_eth"})
        .astype(object)
        .groupby("solver")
        .sum()
    )
    primary_rewards_df["primary_reward_cow"] = (
        primary_rewards_df["primary_reward_eth"]
        .apply(converter.eth_to_token)
        .astype(object)
    )
    return primary_rewards_df


def compute_primary_reward_datum(row: Series) -> tuple[str, int]:
    """Compute the reward of an auction from the winning and references scores"""
    solver = row["winning_solver"]
    if row["tx_hash"] is None:
        reward = -min(row["reference_score"], EPSILON_LOWER)
    else:
        reward = min(row["winning_score"] - row["reference_score"], EPSILON_UPPER)

    return solver, reward


def compute_secondary_rewards_df(
    batch_data_df: DataFrame, primary_rewards_df: DataFrame, converter: TokenConversion
) -> DataFrame:
    """Compute secondary rewards from batch data and primary rewards"""
    secondary_allocation = max(
        min(
            PERIOD_BUDGET_COW - primary_rewards_df["primary_reward_cow"].sum(),
            converter.eth_to_token(CONSISTENCY_REWARD_CAP_ETH),
        ),
        0,
    )
    secondary_rewards_df = (
        batch_data_df["participating_solvers"]
        .explode()
        .value_counts()
        .reset_index()
        .rename(columns={"participating_solvers": "solver", "count": "num_auctions"})
        .astype(object)
    )
    participation_total = secondary_rewards_df["num_auctions"].sum()
    secondary_rewards_df["secondary_reward_cow"] = (
        secondary_allocation * secondary_rewards_df["num_auctions"]
    ) // participation_total
    secondary_rewards_df["secondary_reward_eth"] = (
        secondary_rewards_df["secondary_reward_cow"]
        .apply(converter.token_to_eth)
        .astype(object)
    )
    secondary_rewards_df = secondary_rewards_df.drop("num_auctions", axis=1)

    return secondary_rewards_df


def compute_quote_rewards(
    trade_data_df: DataFrame, converter: TokenConversion
) -> DataFrame:
    """Compute quote rewards from batch data"""
    quote_rewards_df = (
        trade_data_df[trade_data_df.apply(is_market_order, axis=1)]
        .quote_solver.value_counts()
        .reset_index()
        .rename(columns={"quote_solver": "solver", "count": "num_quotes"})
        .apply(
            lambda row: (
                row["solver"],
                int(
                    float(
                        min(
                            QUOTE_REWARD_COW,
                            converter.eth_to_token(QUOTE_REWARD_CAP_ETH),
                        )
                    )
                    * row["num_quotes"]
                ),
            ),
            axis=1,
            result_type="expand",
        )
        .rename(columns={0: "solver", 1: "quote_reward_cow"})
        .astype(object)
    )
    return quote_rewards_df


def is_market_order(row: Series) -> bool:
    """Check if an order was in market when created."""
    try:
        if row["quote_solver"] is None:
            return False
        if row["kind"] == "sell":
            return (
                int(
                    row["quote_sell_amount"]
                    - row["quote_gas_amount"]
                    * row["quote_gas_price"]
                    / row["quote_sell_token_price"]
                )
                * row["quote_buy_amount"]
                >= row["limit_buy_amount"] * row["quote_sell_amount"]
                and not row["partially_fillable"]
            )
        if row["kind"] == "buy":
            return (
                row["limit_sell_amount"]
                >= int(
                    row["quote_sell_amount"]
                    + row["quote_gas_amount"]
                    * row["quote_gas_price"]
                    / row["quote_sell_token_price"]
                )
                and not row["partially_fillable"]
            )
        raise ValueError(
            f"Unknow order kind \"{row['kind']}\". Only \"sell\" and \"buy\" are supported."
        )
    except KeyError:
        return False
