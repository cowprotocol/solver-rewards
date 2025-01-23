"""Functionality for protocol fees."""

from pandas import DataFrame

BATCH_DATA_COLUMNS = ["solver", "protocol_fee_eth"]

PROTOCOL_FEES_COLUMNS = BATCH_DATA_COLUMNS


def compute_protocol_fees(
    batch_data: DataFrame,
) -> DataFrame:
    """Compute protocol fees per solver."""

    # validate batch data columns
    assert set(BATCH_DATA_COLUMNS).issubset(set(batch_data.columns))

    protocol_fees = batch_data[BATCH_DATA_COLUMNS].copy()

    # change all types to object to use native python types
    protocol_fees = protocol_fees.astype(object)

    assert set(protocol_fees.columns) == set(PROTOCOL_FEES_COLUMNS)

    return protocol_fees
