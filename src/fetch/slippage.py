"""Functionality for computing slippage"""

from pandas import DataFrame


def compute_slippage(
    slippage_data_df: DataFrame, trade_fees_df: DataFrame
) -> DataFrame:
    """Compute total slippage from slippage and trade data."""
    # compute network fees
    network_fees_df = (
        trade_fees_df.groupby("winning_solver")
        .network_fee.sum()
        .reset_index()
        .rename(columns={"winning_solver": "solver", "network_fee": "network_fee_eth"})
        .astype(object)
    )

    # combine with dune slippage query
    slippage_df = (
        slippage_data_df.rename(columns={"solver_address": "solver"})
        .merge(network_fees_df, on="solver", how="outer")
        .fillna(0)
        .apply(
            lambda row: (
                row["solver"],
                row["solver_name"],
                int(row["eth_slippage_wei"] + row["network_fee_eth"]),
            ),
            axis=1,
            result_type="expand",
        )
        .rename(columns={0: "solver", 1: "solver_name", 2: "slippage_eth"})
        .astype(object)
    )

    return slippage_df
