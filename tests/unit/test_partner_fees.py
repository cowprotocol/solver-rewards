import pytest
import pandas
from pandas import DataFrame

from src.config import ProtocolFeeConfig, Network
from src.fetch.partner_fees import (
    compute_partner_fees,
    compute_partner_fees_per_partner,
)


def test_compute_partner_fees_per_partner():
    """Test partner fees computation"""
    config = ProtocolFeeConfig.from_network(Network.MAINNET)
    partner_fee_lists = DataFrame(
        {
            "partner_list": [["partner_1", "partner_2"], ["partner_2", "partner_3"]],
            "partner_fee_eth": [[10**16, 10**17], [10**18, 10**19]],
        }
    )

    partner_fees_df = compute_partner_fees_per_partner(partner_fee_lists, config)
    expected_protocol_fees_df = DataFrame(
        {
            "partner": ["partner_1", "partner_2", "partner_3"],
            "partner_fee_eth": [10**16, 10**17 + 10**18, 10**19],
            "partner_fee_tax": [0.5, 0.5, 0.5],
        }
    ).astype(object)

    pandas.testing.assert_frame_equal(partner_fees_df, expected_protocol_fees_df)


def test_compute_partner_fees_per_partner_empty():
    """Test that code also works for empty data."""
    config = ProtocolFeeConfig.from_network(Network.MAINNET)
    partner_fee_lists = DataFrame(
        {
            "partner_list": [],
            "partner_fee_eth": [],
        }
    )

    partner_fees_df = compute_partner_fees_per_partner(partner_fee_lists, config)
    expected_protocol_fees_df = DataFrame(
        {
            "partner": [],
            "partner_fee_eth": [],
            "partner_fee_tax": [],
        }
    ).astype(object)

    pandas.testing.assert_frame_equal(partner_fees_df, expected_protocol_fees_df)


def test_compute_partner_fees_per_partner_reduced_cut():
    """Test reduced cut."""
    config = ProtocolFeeConfig.from_network(Network.MAINNET)
    partner_fee_lists = DataFrame(
        {
            "partner_list": [["0x63695eee2c3141bde314c5a6f89b98e62808d716"]],
            "partner_fee_eth": [[10**18]],
        }
    )

    partner_fees_df = compute_partner_fees_per_partner(partner_fee_lists, config)
    expected_protocol_fees_df = DataFrame(
        {
            "partner": ["0x63695eee2c3141bde314c5a6f89b98e62808d716"],
            "partner_fee_eth": [10**18],
            "partner_fee_tax": [
                config.custom_partner_fee_dict[
                    "0x63695eee2c3141bde314c5a6f89b98e62808d716"
                ]
            ],
        }
    ).astype(object)

    pandas.testing.assert_frame_equal(partner_fees_df, expected_protocol_fees_df)


def test_compute_partner_fees_per_partner_duplicates():
    """Test that code also works for duplicate partner on one solver.
    This is required due to how data is merged if a solver is participating in prod and barn.
    """
    partner_fee_lists = DataFrame(
        {
            "partner_list": [["partner_1", "partner_1"]],
            "partner_fee_eth": [[10**17, 10**18]],
        }
    )
    config = ProtocolFeeConfig.from_network(Network.MAINNET)

    partner_fees_df = compute_partner_fees_per_partner(partner_fee_lists, config)
    expected_protocol_fees_df = DataFrame(
        {
            "partner": ["partner_1"],
            "partner_fee_eth": [10**17 + 10**18],
            "partner_fee_tax": [0.5],
        }
    ).astype(object)

    pandas.testing.assert_frame_equal(partner_fees_df, expected_protocol_fees_df)


def test_compute_partner_fees_wrong_columns():
    """Test column validation"""
    config = ProtocolFeeConfig.from_network(Network.MAINNET)
    wrong_columns = DataFrame({"wrong_column": []})

    with pytest.raises(AssertionError):
        compute_partner_fees(wrong_columns, config)
