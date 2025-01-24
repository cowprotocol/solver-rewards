"""Functionality for solver information."""

import numpy as np
import pandas as pd
from pandas import DataFrame

from src.config import AccountingConfig
from src.logger import set_log

log = set_log(__name__)

REWARD_TARGETS_COLUMNS = ["solver", "reward_target", "pool_address", "solver_name"]
SERVICE_FEES_COLUMNS = ["solver", "service_fee"]

SOLVER_INFO_COLUMNS = [
    "solver",
    "solver_name",
    "reward_target",
    "buffer_accounting_target",
    "service_fee",
]


def compute_solver_info(
    reward_targets: DataFrame,
    service_fees: DataFrame,
    config: AccountingConfig,
) -> DataFrame:
    """Compute solver info.

    Parameters
    ----------
    reward_targets : DataFrame
        Data on reward targets and bonding pools.
        The columns have to contain REWARD_TARGETS_COLUMNS:
        solver : str
            "0x"-prefixed hex representation of the submission address of a solver.
        reward_target : str
            "0x"-prefixed hex representation of the reward target of a solver. All rewards are sent
            to this address.
        pool_address: str
            "0x"-prefixed hex representation of address of a solvers bonding pool.
        solver_name: str
            Name of a solver.
    service_fees : DataFrame
        Service fee data.
        The columns have to contain SERVICE_FEES_COLUMNS:
        solver : str
            "0x"-prefixed hex representation of the submission address of a solver.
        service_fee : bool
            True is a solver needs to pay a service fee to the COW DAO. Otherwise, it is False.
    config : AccountingConfig
        Accounting configuration.

    Returns
    -------
    solver_info : DataFrame
        Data frame containing required information per solver.
        The columns are SOLVER_INFO_COLUMNS:
        solver : str
            "0x"-prefixed hex representation of the submission address of a solver.
        solver_name : str
            Name of a solver.
        reward_target : str
            "0x"-prefixed hex representation of the reward target of a solver. All
            rewards are sent to this address.
        buffer_accounting_target : str
            "0x"-prefixed hex representation of the buffer accounting target address of a solver.
            Results of the buffer accounting are sent to this address. It is equal to `solver` or
            `reward_target`.
        service_fee : Fraction
            The fraction of rewards which need to be paid to the COW DAO.

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

    # validate reward targets and service fees columns
    assert set(REWARD_TARGETS_COLUMNS).issubset(set(reward_targets.columns))
    assert set(SERVICE_FEES_COLUMNS).issubset(set(service_fees.columns))

    solver_info = reward_targets[REWARD_TARGETS_COLUMNS].merge(
        service_fees[SERVICE_FEES_COLUMNS], how="outer", on="solver"
    )

    solver_info["buffer_accounting_target"] = np.where(
        solver_info["pool_address"] != config.reward_config.cow_bonding_pool.address,
        solver_info["solver"],
        solver_info["reward_target"],
    )
    solver_info = solver_info.drop("pool_address", axis=1)

    solver_info["service_fee"] = [
        (
            service_fees_flag * config.reward_config.service_fee_factor
            if not pd.isna(service_fees_flag)
            else 0 * config.reward_config.service_fee_factor
        )
        for service_fees_flag in solver_info["service_fee"]
    ]

    if not solver_info["solver"].is_unique:
        duplicate_solvers = solver_info[solver_info["solver"].duplicated(keep=False)]
        log.warning(f"Duplicate solvers: {duplicate_solvers}. Choosing first entry.")
        solver_info = solver_info.drop_duplicates(subset=["solver"])

    solver_info = solver_info.astype(object)

    assert set(solver_info.columns) == set(SOLVER_INFO_COLUMNS)

    return solver_info
