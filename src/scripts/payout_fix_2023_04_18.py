"""
For the Accounting Period April 11 - 18, 2023 there was a bug
in the backend services attributing incorrect solver reward values
for a substantial number of market orders:

cf. <INCLUDE LINK TO BUG AND FIX>

This script
- fetches the difference between ETH & COW Payments made before and after the fix,
- takes the difference (ignoring what is owed to us) and
- constructs a CSV transfer file making up for anything we owe solvers.
"""
import os
import pandas
from dune_client.client import DuneClient

NUMERICAL_COLUMNS = [
    "eth_transfer",
    "cow_transfer",
]

if __name__ == "__main__":
    # Saved query Executions. Note that before is no longer
    # re-constructable since the query is based on changed data.
    exec_id_before = "01GYFEPH4XV8QJTZ2QSEAE3VWK"
    exec_id_after = "01GYJ7RF07BVWW5SNGYTWYFMG5"

    dune = DuneClient(os.environ["DUNE_API_KEY"])

    before = pandas.read_csv(dune.get_result_csv(exec_id_before).data)
    after = pandas.read_csv(dune.get_result_csv(exec_id_after).data)

    for number_col in NUMERICAL_COLUMNS:
        before[number_col] = before[number_col].replace("<nil>", 0)
        after[number_col] = after[number_col].replace("<nil>", 0)
        before[number_col] = pandas.to_numeric(before[number_col])
        after[number_col] = pandas.to_numeric(after[number_col])

    before = before[
        [
            "solver",
            "name",
            "reward_target",
            "eth_transfer",
            "cow_transfer",
        ]
    ].add_suffix("_before")
    after = after[
        [
            "solver",
            "eth_transfer",
            "cow_transfer",
        ]
    ].add_suffix("_after")

    merged = pandas.merge(
        before, after, left_on="solver_before", right_on="solver_after", how="left"
    )

    merged["owed_eth"] = merged["eth_transfer_after"] - merged["eth_transfer_before"]
    merged["owed_cow"] = merged["cow_transfer_after"] - merged["cow_transfer_before"]
    print(merged)
