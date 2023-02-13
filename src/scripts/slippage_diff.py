import os
from dataclasses import dataclass
import pandas as pd
from dotenv import load_dotenv
from dune_client.client import DuneClient


# @dataclass
# class SolverSlippage:
#     """
#     {
#         "eth_slippage_wei": -141109320862504820,
#         "solver_address": "0xffc5e9d86c0e069f8b037c841acc72cf94eebad8",
#         "solver_name": "barn-Barter",
#         "usd_value": -233.63653303683859
#     },
#     """
#     eth_slippage_wei: int
#     solver_address: str
#     solver_name: str
#     usd_value: float


def get_slippages_for_execution(dune: DuneClient, job_id: str):
    results = pd.DataFrame(dune.get_result(job_id).get_rows())
    results = results.sort_values(by=['solver_address'])
    return results


if __name__ == "__main__":
    bugged_execution = "01GR3DHGXBH6MDBK45G9VWG9VN"
    fixed_execution = "01GS5E51W0P8Z4MC5XH03J7ZBN"
    load_dotenv()
    dune = DuneClient(api_key=os.environ["DUNE_API_KEY"])

    a = get_slippages_for_execution(dune, bugged_execution)
    b = get_slippages_for_execution(dune, fixed_execution)
    b = b.drop("batchwise_breakdown", axis=1)


    # c = a.join(b, on="solver_address")

    a.to_csv("bug_data.csv", index=False)
    b.to_csv("new_data.csv", index=False)
    # z = a.compare(b)






