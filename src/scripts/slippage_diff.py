import os

import pandas as pd
from dotenv import load_dotenv
from dune_client.client import DuneClient
from pandas import DataFrame

from src.fetch.transfer_file import manual_propose
from src.models.slippage import SplitSlippages
from src.utils.script_args import generic_script_init


def get_slippages_for_execution(dune_client: DuneClient, job_id: str) -> DataFrame:
    """Fetches, sorts and returns slippage query results"""
    results = pd.DataFrame(dune_client.get_result(job_id).get_rows())
    results = results.astype({"eth_slippage_wei": int})
    try:
        results = results.drop("batchwise_breakdown", axis=1)
    except KeyError:
        # Dataframe does not have this column
        pass
    results = results.sort_values(by=["solver_address"])
    return results


if __name__ == "__main__":
    args = generic_script_init(description="Fetch Complete Reimbursement")

    # https://production-6de61f.kb.eu-central-1.aws.cloud.es.io/app/r/s/Z4HbA
    bugged_execution = "01GRNEBG085542R4CQAPNNRMSH"

    fixed_execution = "01GS5E51W0P8Z4MC5XH03J7ZBN"
    latest_execution = "01GS7F13SHEYVKYRESCGWTV0R4"

    load_dotenv()
    dune = DuneClient(api_key=os.environ["DUNE_API_KEY"])

    bug_df = get_slippages_for_execution(dune, bugged_execution)
    fix_df = get_slippages_for_execution(dune, fixed_execution)
    latest_df = get_slippages_for_execution(dune, latest_execution)

    bug_df.to_csv("bug_data.csv", index=False)
    fix_df.to_csv("new_data.csv", index=False)
    latest_df.to_csv("latest_data.csv", index=False)

    merged_df = bug_df.merge(
        fix_df,
        on=["solver_address", "solver_name"],
        how="outer",
        suffixes=("_bug", "_fix"),
    )
    merged_df = merged_df.merge(
        latest_df, on=["solver_address", "solver_name"], how="outer"
    ).fillna(0)

    merged_df["adjusted_usd"] = (
        merged_df["usd_value_fix"] - merged_df["usd_value_bug"] + merged_df["usd_value"]
    )
    merged_df["adjusted_eth_slippage_wei"] = (
        merged_df["eth_slippage_wei_fix"]
        - merged_df["eth_slippage_wei_bug"]
        + merged_df["eth_slippage_wei"]
    )

    merged_df.to_csv("final_results.csv", index=False)
    d = merged_df[
        ["solver_address", "solver_name", "adjusted_eth_slippage_wei"]
    ].rename(columns={"adjusted_eth_slippage_wei": "eth_slippage_wei"})

    data_dict = d.to_dict(orient="records")
    slippage = SplitSlippages.from_data_set(data_dict)

    manual_propose(args.dune, slippage)
