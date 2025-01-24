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
    """Compute buffer accounting per solver.

    Parameters
    ----------
    batch_data : DataFrame
        Batch rewards data.
        The columns have to contain BATCH_REWARDS_COLUMNS:
        solver : str
            "0x"-prefixed hex representation of the submission address of a solver.
        network_fee_eth : int
            Network fees in wei of a solver for settling batches.
    slippage_data : DataFrame
        Slippage data.
        The columns have to contain SLIPPAGE_COLUMNS:
        solver : str
            "0x"-prefixed hex representation of the submission address of a solver.
        eth_slippage_wei : int
            Slippage in wei accrued by a solver in settling batches.

    Returns
    -------
    buffer_accounting : DataFrame
        Data frame containing rewards per solver.
        The columns are REWARDS_COLUMNS:
        solver : str
            "0x"-prefixed hex representation of the submission address of a solver.
        network_fee_eth : int
            Network fees in wei of a solver for settling batches.
        slippage_eth : int
            Slippage in wei accrued by a solver in settling batches.

    Raises
    ------
    AssertionError
        If input dataframes do not contain required columns or if the result does not have correct
        columns.

    Notes
    -----
    All data frames are set to have data type `object`. Otherwise, implicit conversion to int64 can
    lead to overflows.
    """

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
