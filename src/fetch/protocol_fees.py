"""Functionality for protocol fees."""

from pandas import DataFrame

BATCH_DATA_COLUMNS = ["solver", "protocol_fee_eth"]

PROTOCOL_FEES_COLUMNS = BATCH_DATA_COLUMNS


def compute_protocol_fees(
    batch_data: DataFrame,
) -> DataFrame:
    """Compute protocol fees.

    Parameters
    ----------
    batch_data : DataFrame
        Batch rewards data.
        The columns have to contain BATCH_DATA_COLUMNS:
        solver : str
            "0x"-prefixed hex representation of the submission address of a solver.
        protocol_fee_eth : int
            Protocol fee of a solver for settling batches in wei.

    Returns
    -------
    protocol_fees : DataFrame
        Data frame containing protocol fees per solver.
        The columns are PROTOCOL_FEES_COLUMNS:
        solver : str
            "0x"-prefixed hex representation of the submission address of a solver.
        protocol_fee_eth : int
            Protocol fee of a solver for settling batches in wei.

    Raises
    ------
    AssertionError
        If input dataframe does not contain required columns or if the result does not have correct
        columns.

    Notes
    -----
    All data frames are set to have data type `object`. Otherwise, implicit conversion to int64 can
    lead to overflows.
    """

    # validate batch data columns
    assert set(BATCH_DATA_COLUMNS).issubset(set(batch_data.columns))

    protocol_fees = batch_data[BATCH_DATA_COLUMNS].copy()

    # change all types to object to use native python types
    protocol_fees = protocol_fees.astype(object)

    assert set(protocol_fees.columns) == set(PROTOCOL_FEES_COLUMNS)

    return protocol_fees
