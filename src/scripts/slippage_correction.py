import os

import pandas as pd
from dune_client.client import DuneClient
from dotenv import load_dotenv

# TODO - Include Whatever Part of May.
months = [1, 2, 3, 4]

OLD_SLIPPAGE_EXECUTION_IDS = {
    1: "01H155A02SH9J58K79KW6581DN",
    2: "01H155MD0SSYDENMWE6Y6DRE37",
    3: "01H15A3JJFH8E9ZSG0GVPN3963",
    4: "01H15ADMN4Q9X63DAW6FVSY1W7",
    # 5: ""
}

NEW_SLIPPAGE_EXECUTION_IDS = {
    1: "01H15924T2A8ZMSDSJXAZTDW7K",
    2: "01H159ED65QE417NWAGFVAC6HB",
    3: "01H171P567EEDSKRYPMP419WR2",
    4: "01H1721SX8XS4HCDVWFHXJQPFA",
    # 5: ""
}


def join_coalesce_fillna(
    df_1: pd.DataFrame, df_2: pd.DataFrame, suffixes: tuple[str, str] = ("_old", "_new")
) -> pd.DataFrame:
    merged = pd.merge(
        df_1, df_2, on="solver_address", how="outer", suffixes=list(suffixes)
    )

    # coalesce solver names
    col = "solver_name"
    merged[col] = merged[f"{col}{suffixes[0]}"].combine_first(
        merged[f"{col}{suffixes[1]}"]
    )
    del merged[f"{col}{suffixes[0]}"]
    del merged[f"{col}{suffixes[1]}"]

    merged.fillna(0, inplace=True)
    return merged


if __name__ == "__main__":
    load_dotenv()
    dune = DuneClient(os.environ["DUNE_API_KEY"])

    month_diffs = {}
    for month in months:
        old_df = pd.read_csv(
            dune.get_result_csv(OLD_SLIPPAGE_EXECUTION_IDS[month]).data
        )
        new_df = pd.read_csv(
            dune.get_result_csv(NEW_SLIPPAGE_EXECUTION_IDS[month]).data
        )

        # Take out the trash
        del old_df["batchwise_breakdown"]
        del new_df["batchwise_breakdown"]

        combined_df = join_coalesce_fillna(old_df, new_df)

        combined_df["eth_diff_wei"] = (
            combined_df["eth_slippage_wei_old"] - combined_df["eth_slippage_wei_new"]
        )
        # These don't actually matter, but we can have them if we want.
        combined_df["us_diff"] = (
            combined_df["usd_value_old"] - combined_df["usd_value_new"]
        )
        # combined_df["eth_diff"] = combined_df["eth_diff_wei"] / 1e18

        month_diffs[month] = combined_df[
            ["solver_address", "solver_name", "eth_diff_wei", "us_diff"]
        ]

    agg_result = pd.DataFrame({"solver_address": [], "solver_name": []})
    for month, diff_df in month_diffs.items():
        agg_result = join_coalesce_fillna(
            agg_result, diff_df, suffixes=(str(month - 1), str(month))
        )

    agg_result["total_wei"] = sum([agg_result[f"eth_diff_wei{i}"] for i in months])
    agg_result["total_us"] = sum([agg_result[f"us_diff{i}"] for i in months])
    agg_result["total_eth"] = agg_result["total"] / 1e18
    agg_result.to_csv("./whateva.csv")
