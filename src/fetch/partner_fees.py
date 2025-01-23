"""Functionality for partner fees."""

from collections import defaultdict

import numpy as np
import pandas as pd
from pandas import DataFrame

from src.config import ProtocolFeeConfig

BATCH_DATA_COLUMNS = ["partner_list", "partner_fee_eth"]

PARTNER_FEES_COLUMNS = ["partner", "partner_fee_eth", "partner_fee_tax"]


def compute_partner_fees(batch_data: DataFrame, config: ProtocolFeeConfig) -> DataFrame:
    """Compute partner fees per integrator"""

    # validate batch data columns
    assert set(BATCH_DATA_COLUMNS).issubset(set(batch_data.columns))

    partner_fee_lists = batch_data[BATCH_DATA_COLUMNS]

    partner_fees = compute_partner_fees_per_partner(partner_fee_lists, config)

    assert set(partner_fees.columns) == set(PARTNER_FEES_COLUMNS)

    return partner_fees


def compute_partner_fees_per_partner(
    partner_fee_lists: DataFrame, config: ProtocolFeeConfig
) -> DataFrame:
    """Aggregate fees from different solvers"""

    partner_fees_dict: defaultdict[str, int] = defaultdict(int)
    for _, row in partner_fee_lists.iterrows():
        if row["partner_list"] is None:
            continue

        # We assume the two lists used below, i.e.,
        # partner_list and partner_fee_eth,
        # are "aligned".

        for partner, partner_fee in zip(row["partner_list"], row["partner_fee_eth"]):
            partner_fees_dict[partner] += int(partner_fee)

    partner_fees_df = pd.DataFrame(
        list(partner_fees_dict.items()),
        columns=["partner", "partner_fee_eth"],
    )

    partner_fees_df["partner_fee_tax"] = np.where(
        partner_fees_df["partner"] == config.reduced_cut_address,
        config.partner_fee_reduced_cut,
        config.partner_fee_cut,
    )

    # change all types to object to use native python types
    partner_fees_df = partner_fees_df.astype(object)

    return partner_fees_df
