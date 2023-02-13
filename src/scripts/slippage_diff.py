import os

import pandas as pd
from dotenv import load_dotenv
from dune_client.client import DuneClient
from pandas import DataFrame


def get_slippages_for_execution(dune_client: DuneClient, job_id: str) -> DataFrame:
    """Fetches, sorts and returns slippage query results"""
    results = pd.DataFrame(dune_client.get_result(job_id).get_rows())
    results = results.sort_values(by=["solver_address"])
    return results


if __name__ == "__main__":
    bugged_execution = "01GR3DHGXBH6MDBK45G9VWG9VN"
    fixed_execution = "01GS5E51W0P8Z4MC5XH03J7ZBN"
    load_dotenv()
    dune = DuneClient(api_key=os.environ["DUNE_API_KEY"])

    bug_df = get_slippages_for_execution(dune, bugged_execution)
    fix_df = get_slippages_for_execution(dune, fixed_execution)
    fix_df = fix_df.drop("batchwise_breakdown", axis=1)

    bug_df.to_csv("bug_data.csv", index=False)
    fix_df.to_csv("new_data.csv", index=False)
