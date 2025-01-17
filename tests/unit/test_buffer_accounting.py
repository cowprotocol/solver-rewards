import pytest
import pandas
from pandas import DataFrame

from src.fetch.buffer_accounting import compute_buffer_accounting


def test_compute_buffer_accounting():
    """Test buffer accounting computation"""
    batch_data = DataFrame(
        {
            "solver": ["solver_1", "solver_2"],
            "network_fee_eth": [10**15, 10**16],
        }
    )
    slippage_data = DataFrame(
        {
            "solver": ["solver_2", "solver_3"],
            "eth_slippage_wei": [10**17, 10**18],
        }
    )

    buffer_accounting = compute_buffer_accounting(batch_data, slippage_data)
    expected_buffer_accounting = DataFrame(
        {
            "solver": ["solver_1", "solver_2", "solver_3"],
            "network_fee_eth": [10**15, 10**16, 0],
            "slippage_eth": [0, 10**17, 10**18],
        }
    ).astype(object)

    pandas.testing.assert_frame_equal(buffer_accounting, expected_buffer_accounting)


def test_compute_buffer_accounting_empty():
    """Test that code also works for empty data."""
    batch_data = DataFrame(
        {
            "solver": [],
            "network_fee_eth": [],
        }
    )
    slippage_data = DataFrame(
        {
            "solver": [],
            "eth_slippage_wei": [],
        }
    )

    buffer_accounting = compute_buffer_accounting(batch_data, slippage_data)
    expected_buffer_accounting = DataFrame(
        {
            "solver": [],
            "network_fee_eth": [],
            "slippage_eth": [],
        }
    ).astype(object)

    pandas.testing.assert_frame_equal(buffer_accounting, expected_buffer_accounting)


def test_compute_protocol_fees_wrong_columns():
    """Test column validation"""
    legit_batch_data = DataFrame(
        {
            "solver": [],
            "network_fee_eth": [],
        }
    )
    legit_slippage_data = DataFrame(
        {
            "solver": [],
            "eth_slippage_wei": [],
        }
    )

    wrong_columns = DataFrame({"wrong_column": []})

    with pytest.raises(AssertionError):
        compute_buffer_accounting(wrong_columns, legit_slippage_data)

    with pytest.raises(AssertionError):
        compute_buffer_accounting(legit_batch_data, wrong_columns)
