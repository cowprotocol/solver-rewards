import pytest
import pandas
from pandas import DataFrame

from src.fetch.protocol_fees import compute_protocol_fees


def test_compute_protocol_fees():
    """Test protocol fees computation"""
    batch_data = DataFrame(
        {
            "solver": ["solver_1", "solver_2"],
            "protocol_fee_eth": [10**15, 10**16],
        }
    )

    protocol_fees = compute_protocol_fees(batch_data)
    expected_protocol_fee = batch_data.astype(object)

    pandas.testing.assert_frame_equal(protocol_fees, expected_protocol_fee)


def test_compute_protocol_fees_empty():
    """Test that code also works for empty data."""
    batch_data = DataFrame(
        {
            "solver": [],
            "protocol_fee_eth": [],
        }
    )

    protocol_fees = compute_protocol_fees(batch_data)
    expected_protocol_fee = DataFrame(
        {
            "solver": [],
            "protocol_fee_eth": [],
        }
    ).astype(object)

    pandas.testing.assert_frame_equal(protocol_fees, expected_protocol_fee)


def test_compute_protocol_fees_wrong_columns():
    """Test column validation"""
    wrong_columns = DataFrame({"wrong_column": []})

    with pytest.raises(AssertionError):
        compute_protocol_fees(wrong_columns)
