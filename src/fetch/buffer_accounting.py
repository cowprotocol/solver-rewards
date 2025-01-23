"""Functionality for buffer accounting."""

import pandas as pd
from pandas import DataFrame

BATCH_DATA_COLUMNS = ["solver", "network_fee_eth"]
SLIPPAGE_COLUMNS = [
    "solver",
    "eth_slippage_wei",
]

BUFFER_ACCOUNTING_COLUMNS = [
    "solver",
    "network_fee_eth",
    "slippage_eth",
]


def compute_buffer_accounting(
    batch_data: DataFrame, slippage_data: DataFrame
) -> DataFrame:
    """Compute buffer accounting per solver"""

    # validate batch data and slippage data columns
    assert set(BATCH_DATA_COLUMNS).issubset(set(batch_data.columns))
    assert set(SLIPPAGE_COLUMNS).issubset(set(slippage_data.columns))

    with pd.option_context(
        "future.no_silent_downcasting", True
    ):  # remove this after Future warning disappears. We do not depend on down-casting,
        # as we will work with object and int explicitly.
        buffer_accounting = (
            (
                batch_data[BATCH_DATA_COLUMNS]
                .astype(object)
                .merge(
                    slippage_data[SLIPPAGE_COLUMNS].astype(object),
                    how="outer",
                    on="solver",
                    validate="one_to_one",
                )
            )
            .fillna(0)
            .astype(object)
        )
    buffer_accounting = buffer_accounting.rename(
        columns={"eth_slippage_wei": "slippage_eth"}
    )

    assert set(buffer_accounting.columns) == set(BUFFER_ACCOUNTING_COLUMNS)

    return buffer_accounting
