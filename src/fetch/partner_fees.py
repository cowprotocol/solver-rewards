"""Functionality for partner fees."""

from collections import defaultdict

import pandas as pd
from pandas import DataFrame

from src.config import ProtocolFeeConfig

BATCH_DATA_COLUMNS = ["partner_list", "partner_fee_eth"]

PARTNER_FEES_COLUMNS = ["partner", "partner_fee_eth", "partner_fee_tax"]


def compute_partner_fees(batch_data: DataFrame, config: ProtocolFeeConfig) -> DataFrame:
    """Compute partner fees per partner.

    Parameters
    ----------
    batch_data : DataFrame
        Batch rewards data.
        The columns have to contain BATCH_DATA_COLUMNS:
        - partner_list : list[tuple[str, str]]
            List of pairs (address, app_code), where address is "0x"-prefixed hex representation
            of the partner addresses and app_code is the relevant app_code. Partner fees are
            paid to these addresses.
        - partner_fee_eth : list[int]
            List of partner fees in wei a solver owes to a partner for settling batches. The list is
            aligned with the respective partners in partner_list.

    config : ProtocolFeeConfig
        Protocol fee configuration.

    Returns
    -------
    partner_fees : DataFrame
        Data frame containing partner fees per partner.
        The columns are PARTNER_FEES_COLUMNS:
        - partner : str
            "0x"-prefixed hex representation of the address of a partner. Partner fees are paid to
            these addresses.
        - partner_fee_eth : int
            Total partner fee in wei of a partner. This amount is reduced by partner_fee_tax before
            payment.
        - partner_fee_tax : Fraction
            The fraction of partner fees which need to be paid to the CoW DAO.

    Raises
    ------
    AssertionError
        If input dataframe does not contain required columns or if the result does not have correct
        columns.
    """

    # validate batch data columns
    assert set(BATCH_DATA_COLUMNS).issubset(set(batch_data.columns))

    partner_fee_lists = batch_data[BATCH_DATA_COLUMNS]

    partner_fees = compute_partner_fees_per_partner(partner_fee_lists, config)

    assert set(partner_fees.columns) == set(PARTNER_FEES_COLUMNS)

    return partner_fees


def get_partner_fee_tax(pair: tuple[str, str], config: ProtocolFeeConfig) -> float:
    """Helper function to determine whether a (partner_recipient, app_code) pair
        has a custom tax policy.

    Parameters
    ----------
    pair : tuple[str, str]
        This is a (recipient_address, app_code) pair.

    config : ProtocolFeeConfig
        Protocol fee configuration.

    Returns
    -------
    float that represents the cut that needs to be applied to the fees collected for that partner
    """
    partner, app_code = pair[0].lower(), pair[1].lower()

    # Check direct match in custom fee dict
    for (k0, k1), v in config.custom_partner_fee_dict.items():
        if partner == k0.lower() and app_code == k1.lower():
            return v

    # Check fallback match where only partner matches
    for (k0, k1), v in config.custom_partner_fee_dict.items():
        if partner == k0.lower() and not k1:
            return v

    # Default fee if no match found
    return config.default_partner_fee_cut


def compute_partner_fees_per_partner(
    partner_fee_lists: DataFrame, config: ProtocolFeeConfig
) -> DataFrame:
    """Compute partner fees per partner.

    This is the main computation step for partner fees. It has the same input and output format as
    `compute_partner_fees`.

    Parameters
    ----------
    partner_fee_lists : DataFrame
        Batch rewards data.
        The columns are BATCH_DATA_COLUMNS:
        - partner_list : list[tuple[str, str]]
            List of pairs (address, app_code), where address is "0x"-prefixed hex representation
            of the partner addresses and app_code is the relevant app_code. Partner fees are
            paid to these addresses.
        - partner_fee_eth : list[int]
            List of partner fees in wei a solver owes to a partner for settling batches. The list is
            aligned with the respective partners in partner_list.

    config : ProtocolFeeConfig
        Protocol fee configuration.

    Returns
    -------
    partner_fees_df : DataFrame
        Data frame containing partner fees per partner.
        The columns are PARTNER_FEES_COLUMNS:
        - partner : str
            "0x"-prefixed hex representation of the address of a partner. Partner fees are paid to
            these addresses.
        - partner_fee_eth : int
            Total partner fee in wei of a partner. This amount is reduced by partner_fee_tax before
            payment.
        - partner_fee_tax : Fraction
            The fraction of partner fees which need to be paid to the CoW DAO.

    Notes
    -----
    All data frames are set to have data type `object`. Otherwise, implicit conversion to int64 can
    lead to overflows.
    """

    partner_fees_dict: defaultdict[tuple[str, str], int] = defaultdict(int)
    for _, row in partner_fee_lists.iterrows():
        if row["partner_list"] is None:
            continue

        # We assume the two lists used below, i.e.,
        # partner_list and partner_fee_eth,
        # are "aligned".

        for partner_app_code_pair, partner_fee in zip(
            row["partner_list"], row["partner_fee_eth"]
        ):
            partner = partner_app_code_pair[0]
            app_code = partner_app_code_pair[1]
            partner_fees_dict[(partner, app_code)] += int(partner_fee)

    partner_fees_df = pd.DataFrame(
        list(partner_fees_dict.items()),
        columns=["partner_app_code_pair", "partner_fee_eth"],
    )

    # Apply function to compute partner fee tax
    partner_fees_df["partner_fee_tax"] = partner_fees_df["partner_app_code_pair"].apply(
        lambda x: get_partner_fee_tax(x, config)
    )
    # Extract 'partner' from tuple and drop original column
    partner_fees_df["partner"] = partner_fees_df["partner_app_code_pair"].apply(
        lambda x: x[0]
    )
    partner_fees_df.drop(columns=["partner_app_code_pair"], inplace=True)

    # Ensure all columns use native Python types
    partner_fees_df = partner_fees_df.astype(object)

    return partner_fees_df
