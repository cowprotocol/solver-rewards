from fractions import Fraction

import pytest
import pandas
from pandas import DataFrame

from src.config import AccountingConfig, Network
from src.fetch.solver_info import compute_solver_info


def test_compute_solver_info():
    """Test protocol fees computation"""
    config = AccountingConfig.from_network(Network.MAINNET)
    reward_targets = DataFrame(
        {
            "solver": ["solver_1", "solver_2", "solver_3"],
            "reward_target": ["target_1", "target_2", "target_3"],
            "pool_address": ["pool_1", "pool_2", "pool_3"],
            "solver_name": ["solver_name_1", "solver_name_2", "solver_name_3"],
        }
    )
    service_fees = DataFrame(
        {
            "solver": [
                "solver_2",
                "solver_3",
            ],  # solver 1 has not service fee status
            "service_fee": [True, False],
        }
    )

    solver_info = compute_solver_info(reward_targets, service_fees, config)
    expected_solver_info = DataFrame(
        {
            "solver": ["solver_1", "solver_2", "solver_3"],
            "reward_target": ["target_1", "target_2", "target_3"],
            "solver_name": ["solver_name_1", "solver_name_2", "solver_name_3"],
            "service_fee": [
                Fraction(0, 1),
                config.reward_config.service_fee_factor,
                Fraction(0, 1),
            ],
            "buffer_accounting_target": ["solver_1", "solver_2", "solver_3"],
        }
    ).astype(object)

    pandas.testing.assert_frame_equal(solver_info, expected_solver_info)


def test_compute_solver_info_cow_dao_buffer_target():
    """Test that buffer accounting target is set to reward target for CoW DAO solvers."""
    config = AccountingConfig.from_network(Network.MAINNET)
    reward_targets = DataFrame(
        {
            "solver": ["solver_1"],
            "reward_target": ["target_1"],
            "pool_address": ["0x5d4020b9261f01b6f8a45db929704b0ad6f5e9e6"],
            "solver_name": ["solver_name_1"],
        }
    )
    service_fees = DataFrame(
        {
            "solver": [],
            "service_fee": [],
        }
    )

    solver_info = compute_solver_info(reward_targets, service_fees, config)
    expected_solver_info = DataFrame(
        {
            "solver": ["solver_1"],
            "reward_target": ["target_1"],
            "solver_name": ["solver_name_1"],
            "service_fee": [Fraction(0, 1)],
            "buffer_accounting_target": ["target_1"],
        }
    ).astype(object)

    pandas.testing.assert_frame_equal(solver_info, expected_solver_info)


def test_compute_solver_info_drop_duplicate():
    """Test that for duplicate entries the first solver is chosen."""
    config = AccountingConfig.from_network(Network.MAINNET)
    reward_targets = DataFrame(
        {
            "solver": ["solver_1", "solver_1"],
            "reward_target": ["target_1", "target_2"],
            "pool_address": ["pool_1", "pool_2"],
            "solver_name": ["solver_name_1", "solver_name_2"],
        }
    )
    service_fees = DataFrame(
        {
            "solver": [],
            "service_fee": [],
        }
    )

    solver_info = compute_solver_info(reward_targets, service_fees, config)
    expected_solver_info = DataFrame(
        {
            "solver": ["solver_1"],
            "reward_target": ["target_1"],
            "solver_name": ["solver_name_1"],
            "service_fee": [Fraction(0, 1)],
            "buffer_accounting_target": ["solver_1"],
        }
    ).astype(object)

    pandas.testing.assert_frame_equal(solver_info, expected_solver_info)


def test_compute_solver_info_empty():
    """Test that code also works for empty data."""
    config = AccountingConfig.from_network(Network.MAINNET)
    reward_targets = DataFrame(
        {
            "solver": [],
            "reward_target": [],
            "pool_address": [],
            "solver_name": [],
        }
    )
    service_fees = DataFrame(
        {
            "solver": [],
            "service_fee": [],
        }
    )

    solver_info = compute_solver_info(reward_targets, service_fees, config)
    expected_solver_info = DataFrame(
        {
            "solver": [],
            "reward_target": [],
            "solver_name": [],
            "service_fee": [],
            "buffer_accounting_target": [],
        }
    ).astype(object)

    pandas.testing.assert_frame_equal(solver_info, expected_solver_info)


def test_compute_solver_info_wrong_columns():
    """Test column validation"""
    config = AccountingConfig.from_network(Network.MAINNET)
    legit_reward_targets = DataFrame(
        {
            "solver": [],
            "reward_target": [],
            "pool_address": [],
            "solver_name": [],
        }
    )
    legit_service_fees = DataFrame(
        {
            "solver": [],
            "service_fee": [],
        }
    )
    wrong_columns = DataFrame({"wrong_column": []})

    with pytest.raises(AssertionError):
        compute_solver_info(wrong_columns, legit_service_fees, config)

    with pytest.raises(AssertionError):
        compute_solver_info(legit_reward_targets, wrong_columns, config)
