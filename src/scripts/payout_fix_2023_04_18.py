"""
For the Accounting Period April 11 - 18, 2023 there was a bug
in the backend services attributing incorrect solver reward values
for a substantial number of market orders:

cf. https://github.com/cowprotocol/orderbook-queries/pull/1

This script
- fetches the difference between ETH & COW Payments made before and after the fix,
- takes the difference (ignoring what is owed to us) and
- constructs a CSV transfer file making up for anything we owe solvers.
"""
import os
import pandas
from dune_client.client import DuneClient
from dune_client.types import Address

from src.constants import COW_TOKEN_ADDRESS
from src.fetch.transfer_file import manual_propose
from src.models.accounting_period import AccountingPeriod
from src.models.token import Token
from src.models.transfer import Transfer

NUMERICAL_COLUMNS = [
    "eth_transfer",
    "cow_transfer",
]

if __name__ == "__main__":
    # Saved query Executions. Note that before is no longer
    # re-constructable since the query is based on changed data.
    EXEC_ID_BEFORE = "01GYFEPH4XV8QJTZ2QSEAE3VWK"
    EXEC_ID_AFTER = "01GYJ7RF07BVWW5SNGYTWYFMG5"

    dune = DuneClient(os.environ["DUNE_API_KEY"])

    before = pandas.read_csv(dune.get_result_csv(EXEC_ID_BEFORE).data)
    after = pandas.read_csv(dune.get_result_csv(EXEC_ID_AFTER).data)

    for number_col in NUMERICAL_COLUMNS:
        for frame in [before, after]:
            frame[number_col] = frame[number_col].replace("<nil>", 0)
            frame[number_col] = pandas.to_numeric(frame[number_col])

    before = before[["solver", "reward_target", "name", "eth_transfer", "cow_transfer"]]
    after = after[["solver", "eth_transfer", "cow_transfer"]]

    merged = pandas.merge(before, after, on="solver", suffixes=["_before", "_after"])

    merged = merged.sort_values("solver")

    merged["owed_eth"] = merged["eth_transfer_after"] - merged["eth_transfer_before"]
    merged["owed_cow"] = merged["cow_transfer_after"] - merged["cow_transfer_before"]

    merged.to_csv(os.path.join("./out/transfers.csv"), index=False)

    # Filter all owed worth at least ~1 USD.
    # TODO - use current prices to determine amount.
    #  https://github.com/cowprotocol/solver-rewards/issues/256
    owed_eth = merged[merged["owed_eth"] > 0.001]
    owed_cow = merged[merged["owed_cow"] > 10]

    eth_transfers = list(
        owed_eth.apply(
            lambda row: Transfer(
                token=None,
                recipient=Address(row["solver"]),
                amount_wei=row["owed_eth"] * 1e18,
            ),
            axis=1,
        )
    )

    cow_transfers = list(
        owed_cow.apply(
            lambda row: Transfer(
                token=Token(COW_TOKEN_ADDRESS),
                recipient=Address(row["reward_target"]),
                amount_wei=row["owed_cow"] * 1e18,
            ),
            axis=1,
        )
    )

    manual_propose(eth_transfers + cow_transfers, AccountingPeriod("2023-04-11"))
