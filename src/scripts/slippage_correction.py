"""Basic script combining a bunch of Dune CSV results to correct Slippage calculation."""
import os

import pandas as pd
from dune_client.client import DuneClient
from dotenv import load_dotenv

# TODO - Include Whatever Part of May.
months = [1, 2, 3, 4, 5]

OLD_SLIPPAGE_EXECUTION_IDS = {
    1: "01H155A02SH9J58K79KW6581DN",
    2: "01H155MD0SSYDENMWE6Y6DRE37",
    3: "01H15A3JJFH8E9ZSG0GVPN3963",
    4: "01H15ADMN4Q9X63DAW6FVSY1W7",
    5: "01H4DSXSK7FZD14BQ8FKFKV43X",
}

NEW_SLIPPAGE_EXECUTION_IDS = {
    1: "01H15924T2A8ZMSDSJXAZTDW7K",
    2: "01H159ED65QE417NWAGFVAC6HB",
    3: "01H171P567EEDSKRYPMP419WR2",
    4: "01H1721SX8XS4HCDVWFHXJQPFA",
    5: "01H4DSKSGV0FT5CMJVBZ7NQEJQ",
}

PER_TX_SLIPPAGE = {
    "new": "01H19PW76SB71Y1W6WF0ZJD409",
    "old": "01H19PQE2APRXGM01F8X7H71WY",
}


def join_coalesce_fillna(
    df_1: pd.DataFrame,
    df_2: pd.DataFrame,
    suffixes: tuple[str, str] = ("_old", "_new"),
    join_col: str | list[str] = "solver_address",
) -> pd.DataFrame:
    """
    Joins `df_1` and `df_2` on column `join_col` with name suffixes provided (or old-new)
    """
    merged = pd.merge(df_1, df_2, on=join_col, how="outer", suffixes=list(suffixes))
    try:
        # coalesce solver names
        col = "solver_name"
        merged[col] = merged[f"{col}{suffixes[0]}"].combine_first(
            merged[f"{col}{suffixes[1]}"]
        )
        merged.drop(f"{col}{suffixes[0]}", axis=1, inplace=True)
        merged.drop(f"{col}{suffixes[1]}", axis=1, inplace=True)

    except KeyError:
        # No solver name column.
        pass

    merged.fillna(0, inplace=True)
    return merged


def compute_slippage_correction(dune: DuneClient) -> None:
    """Slippage Correction over months."""
    month_diffs = {}
    desired_columns = ["solver_address", "solver_name", "usd_value", "eth_slippage_wei"]
    for month in months:
        old_df = pd.read_csv(
            dune.get_result_csv(OLD_SLIPPAGE_EXECUTION_IDS[month]).data,
            usecols=desired_columns,
        )
        new_df = pd.read_csv(
            dune.get_result_csv(NEW_SLIPPAGE_EXECUTION_IDS[month]).data,
            usecols=desired_columns,
        )

        combined_df = join_coalesce_fillna(
            old_df, new_df, join_col=["solver_address", "solver_name"]
        )

        combined_df["eth_diff_wei"] = (
            combined_df["eth_slippage_wei_old"] - combined_df["eth_slippage_wei_new"]
        )
        # These don't actually matter, but we can have them if we want.
        combined_df["us_diff"] = (
            combined_df["usd_value_old"] - combined_df["usd_value_new"]
        )

        month_diffs[month] = combined_df[
            ["solver_address", "solver_name", "eth_diff_wei", "us_diff"]
        ]

    agg_result = pd.DataFrame({"solver_address": [], "solver_name": []})
    for month, diff_df in month_diffs.items():
        agg_result = join_coalesce_fillna(
            agg_result, diff_df, suffixes=(str(month - 1), str(month))
        )

    agg_result["total_wei"] = sum(agg_result[f"eth_diff_wei{i}"] for i in months)
    agg_result["total_us"] = sum(agg_result[f"us_diff{i}"] for i in months)
    agg_result["total_eth"] = agg_result["total_wei"] / 1e18

    agg_result.to_csv("./data/slippage_correction.csv", index=False)


def compute_large_diffs_per_tx(dune: DuneClient) -> None:
    """Largest differences in slippage per transaction"""
    per_tx_df = join_coalesce_fillna(
        df_1=pd.read_csv(dune.get_result_csv(PER_TX_SLIPPAGE["old"]).data),
        df_2=pd.read_csv(dune.get_result_csv(PER_TX_SLIPPAGE["new"]).data),
        join_col="tx_hash",
    )
    per_tx_df["diff_us"] = per_tx_df["usd_value_new"] - per_tx_df["usd_value_old"]

    # Everything differing by 100 USD in absolute value.
    reduced = per_tx_df[abs(per_tx_df["diff_us"]) > 100]
    reduced.to_csv("./data/biggest_diff.csv", index=False)


if __name__ == "__main__":
    load_dotenv()
    dune_client = DuneClient(os.environ["DUNE_API_KEY"])
    compute_slippage_correction(dune_client)
    compute_large_diffs_per_tx(dune_client)
