"""Functionality for buffer accounting."""

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

    # validate batch rewards and quote rewards columns
    assert set(BATCH_DATA_COLUMNS).issubset(set(batch_data.columns))
    assert set(SLIPPAGE_COLUMNS).issubset(set(slippage_data.columns))

    buffer_accounting = batch_data[BATCH_DATA_COLUMNS].merge(
        slippage_data[SLIPPAGE_COLUMNS], how="outer", on="solver", validate="one_to_one"
    )
    buffer_accounting = buffer_accounting.rename(
        columns={"eth_slippage_wei": "slippage_eth"}
    )

    # change all types to object to use native python types
    buffer_accounting = buffer_accounting.astype(object)

    assert set(buffer_accounting.columns) == set(BUFFER_ACCOUNTING_COLUMNS)

    return buffer_accounting
