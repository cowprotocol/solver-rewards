from fractions import Fraction

import pytest
import pandas
from dune_client.types import Address
from pandas import DataFrame

from src.config import AccountingConfig, Network
from src.fetch.payouts import (
    compute_solver_payouts,
    compute_partner_payouts,
    normalize_address_field,
    validate_df_columns,
    prepare_payouts,
    RewardAndPenaltyDatum,
    SOLVER_PAYOUTS_COLUMNS,
    SOLVER_INFO_COLUMNS,
    REWARDS_COLUMNS,
    PROTOCOL_FEES_COLUMNS,
    BUFFER_ACCOUNTING_COLUMNS,
)
from src.models.accounting_period import AccountingPeriod
from src.models.overdraft import Overdraft
from src.models.token import Token
from src.models.transfer import Transfer


def test_normalize_address_field():
    # lower case value
    column = "aDdReSs"
    value = "AbCd"

    test_df = DataFrame({column: [value]})
    normalize_address_field(test_df, column)
    pandas.testing.assert_frame_equal(test_df, DataFrame({column: [value.lower()]}))

    # no rows in dataframe
    test_df = DataFrame({column: []})
    normalize_address_field(test_df, column)
    pandas.testing.assert_frame_equal(test_df, DataFrame({column: []}))


def test_validate_df_columns():
    legit_solver_info = DataFrame(
        {
            "solver": [],
            "reward_target": [],
            "buffer_accounting_target": [],
            "solver_name": [],
            "service_fee": [],
        }
    )
    legit_rewards = DataFrame(
        {
            "solver": [],
            "primary_reward_eth": [],
            "primary_reward_cow": [],
            "quote_reward_cow": [],
            "reward_token_address": [],
        }
    )
    legit_protocol_fees = DataFrame({"solver": [], "protocol_fee_eth": []})
    legit_buffer_accounting = DataFrame(
        {"solver": [], "network_fee_eth": [], "slippage_eth": []}
    )

    failing_df = DataFrame({})

    with pytest.raises(AssertionError):
        validate_df_columns(
            solver_info=legit_solver_info,
            rewards=legit_rewards,
            protocol_fees=legit_protocol_fees,
            buffer_accounting=failing_df,
        )
    with pytest.raises(AssertionError):
        validate_df_columns(
            solver_info=legit_solver_info,
            rewards=legit_rewards,
            protocol_fees=failing_df,
            buffer_accounting=legit_buffer_accounting,
        )
    with pytest.raises(AssertionError):
        validate_df_columns(
            solver_info=legit_solver_info,
            rewards=failing_df,
            protocol_fees=legit_protocol_fees,
            buffer_accounting=legit_buffer_accounting,
        )
    with pytest.raises(AssertionError):
        validate_df_columns(
            solver_info=failing_df,
            rewards=legit_rewards,
            protocol_fees=legit_protocol_fees,
            buffer_accounting=legit_buffer_accounting,
        )

    validate_df_columns(
        solver_info=legit_solver_info,
        rewards=legit_rewards,
        protocol_fees=legit_protocol_fees,
        buffer_accounting=legit_buffer_accounting,
    )


def test_compute_solver_payouts_empty():
    solver_info = DataFrame(
        {
            "solver": [],
            "reward_target": [],
            "buffer_accounting_target": [],
            "solver_name": [],
            "service_fee": [],
        }
    )
    rewards = DataFrame(
        {
            "solver": [],
            "primary_reward_eth": [],
            "primary_reward_cow": [],
            "quote_reward_cow": [],
            "reward_token_address": [],
        }
    )
    protocol_fees = DataFrame({"solver": [], "protocol_fee_eth": []})
    buffer_accounting = DataFrame(
        {"solver": [], "network_fee_eth": [], "slippage_eth": []}
    )

    solver_payouts = compute_solver_payouts(
        solver_info, rewards, protocol_fees, buffer_accounting
    )
    expected_solver_payouts = DataFrame(
        {column: [] for column in SOLVER_PAYOUTS_COLUMNS}
    )

    pandas.testing.assert_frame_equal(solver_payouts, expected_solver_payouts)


def test_compute_solver_payouts():
    payouts_data = DataFrame(
        {
            "solver": ["solver_1"],
            "reward_target": ["reward_target_1"],
            "buffer_accounting_target": ["buffer_target_1"],
            "solver_name": ["solver_name_1"],
            "service_fee": [Fraction(11, 100)],
            "primary_reward_eth": [10**16],
            "primary_reward_cow": [10**19],
            "quote_reward_cow": [10**20],
            "reward_token_address": ["cow_token_address"],
            "protocol_fee_eth": [10**14],
            "network_fee_eth": [10**13],
            "slippage_eth": [10**12],
        }
    )
    solver_info = payouts_data[SOLVER_INFO_COLUMNS]
    rewards = payouts_data[REWARDS_COLUMNS]
    protocol_fees = payouts_data[PROTOCOL_FEES_COLUMNS]
    buffer_accounting = payouts_data[BUFFER_ACCOUNTING_COLUMNS]

    solver_payouts = compute_solver_payouts(
        solver_info, rewards, protocol_fees, buffer_accounting
    )
    expected_solver_payouts = payouts_data[SOLVER_PAYOUTS_COLUMNS]

    pandas.testing.assert_frame_equal(solver_payouts, expected_solver_payouts)


def test_compute_solver_payouts_defaults():
    """Test default values when some information is missing after joins."""
    solver_info = DataFrame(
        {
            "solver": ["solver_1", "solver_2", "solver_3", "solver_4"],
            "solver_name": [  # all solvers need a name at the moment
                "solver_name_1",
                "solver_name_2",
                "solver_name_3",
                "solver_name_4",
            ],
            "reward_target": [
                None,
                "reward_target_2",  # solver 2 gets rewards and also needs to have a reward target
                None,
                None,
            ],
            "buffer_accounting_target": [
                None,
                None,
                None,
                "buffer_target_4",  # solver 4 gets slippage so they need to have a buffer target
            ],
            "service_fee": [
                None,
                Fraction(11, 100),
                None,
                None,
            ],
        }
    )
    rewards = DataFrame(
        {
            "solver": ["solver_2"],
            "primary_reward_eth": [10**16],
            "primary_reward_cow": [10**19],
            "quote_reward_cow": [10**20],
            "reward_token_address": ["cow_token_address"],
        }
    )
    protocol_fees = DataFrame({"solver": ["solver_3"], "protocol_fee_eth": [10**14]})
    buffer_accounting = DataFrame(
        {
            "solver": ["solver_4"],
            "network_fee_eth": [10**13],
            "slippage_eth": [10**12],
        }
    )

    solver_payouts = compute_solver_payouts(
        solver_info, rewards, protocol_fees, buffer_accounting
    )
    expected_solver_payouts = DataFrame(
        {
            "solver": ["solver_2", "solver_3", "solver_4"],
            "solver_name": [
                "solver_name_2",
                "solver_name_3",
                "solver_name_4",
            ],
            "primary_reward_eth": [10**16, 0, 0],
            "primary_reward_cow": [10**19, 0, 0],
            "quote_reward_cow": [10**20, 0, 0],
            "protocol_fee_eth": [0, 10**14, 0],
            "network_fee_eth": [0, 0, 10**13],
            "slippage_eth": [0, 0, 10**12],
            "reward_target": [
                "reward_target_2",  # solver 2 gets rewards and also needs to have a reward target
                None,
                None,
            ],
            "buffer_accounting_target": [
                None,
                None,
                "buffer_target_4",  # solver 4 gets slippage so they need to have a buffer target
            ],
            "reward_token_address": ["cow_token_address", None, None],
            "service_fee": [
                Fraction(11, 100),
                Fraction(0, 1),
                Fraction(0, 1),
            ],
        }
    )

    pandas.testing.assert_frame_equal(solver_payouts, expected_solver_payouts)


# class TestPayoutTransformations(unittest.TestCase):
#     """Contains tests all stray methods in src/fetch/payouts.py"""
#
#     def setUp(self) -> None:
#         self.config = AccountingConfig.from_network(Network.MAINNET)
#         self.solvers = list(
#             map(
#                 str,
#                 [
#                     Address.from_int(1),
#                     Address.from_int(2),
#                     Address.from_int(3),
#                     Address.from_int(4),
#                 ],
#             )
#         )
#         self.num_quotes = [0, 0, 10, 20]
#         self.reward_targets = list(
#             map(
#                 str,
#                 [
#                     Address.from_int(5),
#                     Address.from_int(6),
#                     Address.from_int(7),
#                     Address.from_int(8),
#                 ],
#             )
#         )
#         self.pool_addresses = list(
#             map(
#                 str,
#                 [
#                     self.config.reward_config.cow_bonding_pool,
#                     Address.from_int(10),
#                     Address.from_int(11),
#                     Address.from_int(12),
#                 ],
#             )
#         )
#         self.service_fee = [
#             Fraction(0, 100),
#             Fraction(0, 100),
#             Fraction(0, 100),
#             Fraction(15, 100),
#         ]
#
#         self.primary_reward_eth = [
#             600000000000000.00000,
#             12000000000000000.00000,
#             -10000000000000000.00000,
#             0.00000,
#         ]
#
#         self.protocol_fee_eth = [
#             1000000000000000.0,
#             2000000000000000.0,
#             0.0,
#             0.0,
#         ]
#         self.network_fee_eth = [
#             2000000000000000.0,
#             4000000000000000.0,
#             0.0,
#             0.0,
#         ]
#         # Mocking TokenConversion!
#         self.mock_converter = TokenConversion(eth_to_token=lambda t: int(t * 1000))
#
#     def test_extend_payment_df(self):
#         base_data_dict = {
#             "solver": self.solvers,
#             "num_quotes": self.num_quotes,
#             "primary_reward_eth": self.primary_reward_eth,
#             "protocol_fee_eth": self.protocol_fee_eth,
#             "network_fee_eth": self.network_fee_eth,
#         }
#         base_payout_df = DataFrame(base_data_dict)
#         result = extend_payment_df(
#             base_payout_df, converter=self.mock_converter, config=self.config
#         )
#         expected_data_dict = {
#             "solver": self.solvers,
#             "num_quotes": self.num_quotes,
#             "primary_reward_eth": [
#                 600000000000000.00000,
#                 12000000000000000.00000,
#                 -10000000000000000.00000,
#                 0.00000,
#             ],
#             "protocol_fee_eth": self.protocol_fee_eth,
#             "network_fee_eth": self.network_fee_eth,
#             "primary_reward_cow": [
#                 600000000000000000.0,
#                 12000000000000000000.0,
#                 -10000000000000000000.0,
#                 0.0,
#             ],
#             "quote_reward_cow": [
#                 0.00000,
#                 0.00000,
#                 6000000000000000000.00000,
#                 12000000000000000000.00000,
#             ],
#         }
#         expected = DataFrame(expected_data_dict)
#         self.assertEqual(set(result.columns), set(expected.columns))
#         self.assertIsNone(pandas.testing.assert_frame_equal(expected, result))
#
#
#
#     def test_construct_payouts(self):
#         payments = extend_payment_df(
#             pdf=DataFrame(
#                 {
#                     "solver": self.solvers,
#                     "num_quotes": self.num_quotes,
#                     "primary_reward_eth": self.primary_reward_eth,
#                     "protocol_fee_eth": self.protocol_fee_eth,
#                     "network_fee_eth": self.network_fee_eth,
#                 }
#             ),
#             converter=self.mock_converter,
#             config=self.config,
#         )
#
#         slippages = DataFrame(
#             {
#                 "solver": self.solvers[:3],
#                 # Note that one of the solvers did not appear,
#                 # in this list (we are testing the left join)
#                 "eth_slippage_wei": [1, 0, -1],
#             }
#         )
#
#         reward_targets = DataFrame(
#             {
#                 "solver": self.solvers,
#                 "solver_name": ["S_1", "S_2", "S_3", "S_4"],
#                 "reward_target": self.reward_targets,
#                 "pool_address": self.pool_addresses,
#             }
#         )
#
#         service_fee_df = DataFrame(
#             {"solver": self.solvers, "service_fee": self.service_fee}
#         )
#
#         result = construct_payout_dataframe(
#             payment_df=payments,
#             slippage_df=slippages,
#             reward_target_df=reward_targets,
#             service_fee_df=service_fee_df,
#             config=self.config,
#         )
#         expected = DataFrame(
#             {
#                 "buffer_accounting_target": [
#                     "0x0000000000000000000000000000000000000005",
#                     str(self.solvers[1]),
#                     str(self.solvers[2]),
#                     str(self.solvers[3]),
#                 ],
#                 "eth_slippage_wei": [2000000000000001.0, 4000000000000000.0, -1.0, 0.0],
#                 "network_fee_eth": [
#                     2000000000000000.0,
#                     4000000000000000.0,
#                     0.0,
#                     0.0,
#                 ],
#                 "pool_address": [
#                     str(self.config.reward_config.cow_bonding_pool),
#                     "0x0000000000000000000000000000000000000010",
#                     "0x0000000000000000000000000000000000000011",
#                     "0x0000000000000000000000000000000000000012",
#                 ],
#                 "primary_reward_cow": [
#                     600000000000000000.0,
#                     12000000000000000000.0,
#                     -10000000000000000000.0,
#                     0.0,
#                 ],
#                 "primary_reward_eth": [600000000000000.0, 1.2e16, -1e16, 0.0],
#                 "protocol_fee_eth": [
#                     1000000000000000.0,
#                     2000000000000000.0,
#                     0.0,
#                     0.0,
#                 ],
#                 "quote_reward_cow": [
#                     0.00000,
#                     0.00000,
#                     6000000000000000000.00000,
#                     12000000000000000000.00000,
#                 ],
#                 "reward_target": [
#                     "0x0000000000000000000000000000000000000005",
#                     "0x0000000000000000000000000000000000000006",
#                     "0x0000000000000000000000000000000000000007",
#                     "0x0000000000000000000000000000000000000008",
#                 ],
#                 "reward_token_address": [
#                     str(self.config.reward_config.reward_token_address),
#                     str(self.config.reward_config.reward_token_address),
#                     str(self.config.reward_config.reward_token_address),
#                     str(self.config.reward_config.reward_token_address),
#                 ],
#                 "service_fee": [
#                     Fraction(0, 100),
#                     Fraction(0, 100),
#                     Fraction(0, 100),
#                     Fraction(15, 100),
#                 ],
#                 "solver": self.solvers,
#                 "solver_name": ["S_1", "S_2", "S_3", "S_4"],
#             }
#         )
#
#         self.assertIsNone(
#             pandas.testing.assert_frame_equal(
#                 expected, result.reindex(sorted(result.columns), axis=1)
#             )
#         )
#
#     def test_prepare_transfers(self):
#         # Need Example of every possible scenario
#         full_payout_data = DataFrame(
#             {
#                 "solver": self.solvers,
#                 "num_quotes": self.num_quotes,
#                 "primary_reward_eth": [600000000000000.0, 1.2e16, -1e16, 0.0],
#                 "protocol_fee_eth": self.protocol_fee_eth,
#                 "network_fee_eth": [100.0, 200.0, 300.0, 0.0],
#                 "primary_reward_cow": [
#                     600000000000000000.0,
#                     12000000000000000000.0,
#                     -10000000000000000000.0,
#                     0.0,
#                 ],
#                 "quote_reward_cow": [
#                     0.00000,
#                     0.00000,
#                     90000000000000000000.00000,
#                     180000000000000000000.00000,
#                 ],
#                 "solver_name": ["S_1", "S_2", "S_3", None],
#                 "eth_slippage_wei": [1.0, 0.0, -1.0, None],
#                 "reward_target": [
#                     "0x0000000000000000000000000000000000000005",
#                     "0x0000000000000000000000000000000000000006",
#                     "0x0000000000000000000000000000000000000007",
#                     "0x0000000000000000000000000000000000000008",
#                 ],
#                 "pool_address": [
#                     "0x5d4020b9261f01b6f8a45db929704b0ad6f5e9e6",
#                     "0x0000000000000000000000000000000000000026",
#                     "0x0000000000000000000000000000000000000027",
#                     "0x0000000000000000000000000000000000000028",
#                 ],
#                 "service_fee": [
#                     Fraction(0, 100),
#                     Fraction(0, 100),
#                     Fraction(0, 100),
#                     Fraction(15, 100),
#                 ],
#                 "buffer_accounting_target": [
#                     self.solvers[0],
#                     "0x0000000000000000000000000000000000000006",
#                     "0x0000000000000000000000000000000000000007",
#                     "0x0000000000000000000000000000000000000008",
#                 ],
#                 "reward_token_address": [
#                     str(self.config.reward_config.reward_token_address),
#                     str(self.config.reward_config.reward_token_address),
#                     str(self.config.reward_config.reward_token_address),
#                     str(self.config.reward_config.reward_token_address),
#                 ],
#             }
#         )
#         period = AccountingPeriod("1985-03-10", 1)
#         protocol_fee_amount = sum(self.protocol_fee_eth)
#         payout_transfers = prepare_transfers(
#             full_payout_data, period, protocol_fee_amount, 0, {}, self.config
#         )
#         self.assertEqual(
#             [
#                 Transfer(
#                     token=None,
#                     recipient=Address(self.solvers[0]),
#                     amount_wei=1,
#                 ),
#                 Transfer(
#                     token=Token(self.config.payment_config.cow_token_address),
#                     recipient=Address(self.reward_targets[0]),
#                     amount_wei=600000000000000000,
#                 ),
#                 Transfer(
#                     token=Token(self.config.payment_config.cow_token_address),
#                     recipient=Address(self.reward_targets[1]),
#                     amount_wei=12000000000000000000,
#                 ),
#                 Transfer(
#                     token=Token(self.config.payment_config.cow_token_address),
#                     recipient=Address(self.reward_targets[2]),
#                     amount_wei=90000000000000000000,
#                 ),
#                 Transfer(
#                     token=Token(self.config.payment_config.cow_token_address),
#                     recipient=Address(self.reward_targets[3]),
#                     amount_wei=int(
#                         180000000000000000000
#                         * (1 - self.config.reward_config.service_fee_factor)
#                     ),
#                 ),
#                 Transfer(
#                     token=None,
#                     recipient=self.config.protocol_fee_config.protocol_fee_safe,
#                     amount_wei=3000000000000000,
#                 ),
#             ],
#             payout_transfers.transfers,
#         )
#
#         self.assertEqual(
#             payout_transfers.overdrafts,
#             [
#                 Overdraft(
#                     period,
#                     account=Address(self.solvers[2]),
#                     wei=10000000000000001,
#                     name="S_3",
#                 )
#             ],
#         )


@pytest.fixture
def common_reward_data() -> dict:
    data: dict = {}
    data["config"] = AccountingConfig.from_network(Network.MAINNET)
    data["solver"] = Address.from_int(1)
    data["solver_name"] = "Solver1"
    data["reward_target"] = Address.from_int(2)
    data["buffer_accounting_target"] = Address.from_int(3)
    data["cow_token_address"] = data["config"].payment_config.cow_token_address
    data["cow_token"] = Token(data["cow_token_address"])
    data["conversion_rate"] = 1000

    return data


def sample_record(
    reward_data,
    primary_reward: int,
    slippage: int,
    num_quotes: int,
    service_fee: Fraction = Fraction(0, 1),
) -> RewardAndPenaltyDatum:
    """Assumes a conversion rate of ETH:COW <> 1:self.conversion_rate"""
    return RewardAndPenaltyDatum(
        solver=reward_data["solver"],
        solver_name=reward_data["solver_name"],
        reward_target=reward_data["reward_target"],
        buffer_accounting_target=reward_data["buffer_accounting_target"],
        primary_reward_eth=primary_reward,
        primary_reward_cow=primary_reward * reward_data["conversion_rate"],
        slippage_eth=slippage,
        quote_reward_cow=reward_data["config"].reward_config.quote_reward_cow
        * num_quotes,
        service_fee=service_fee,
        reward_token_address=reward_data["cow_token_address"],
    )


def test_invalid_input(common_reward_data):
    """Test that negative and quote rewards throw an error."""

    # invalid quote reward
    with pytest.raises(AssertionError):
        sample_record(common_reward_data, 0, 0, -1)


def test_reward_datum_0_0_0(common_reward_data):
    """Without data there is no payout and no overdraft."""
    test_datum = sample_record(common_reward_data, 0, 0, 0)
    assert not test_datum.is_overdraft()
    assert test_datum.as_payouts() == []


def test_reward_datum_pm1_0_0(common_reward_data):
    """Primary reward only."""

    # positive reward is paid in COW
    primary_reward = 1
    test_datum = sample_record(common_reward_data, primary_reward, 0, 0)
    assert not test_datum.is_overdraft()
    assert test_datum.as_payouts() == [
        Transfer(
            token=common_reward_data["cow_token"],
            recipient=common_reward_data["reward_target"],
            amount_wei=primary_reward * common_reward_data["conversion_rate"],
        )
    ]

    # negative reward gives overdraft
    primary_reward = -1
    test_datum = sample_record(common_reward_data, primary_reward, 0, 0)
    assert test_datum.is_overdraft()
    assert test_datum.as_payouts() == []


def test_reward_datum_0_pm1_0(common_reward_data):
    """Slippag only."""

    # positive slippage is paid in ETH
    slippage = 1
    test_datum = sample_record(common_reward_data, 0, slippage, 0)
    assert not test_datum.is_overdraft()
    assert test_datum.as_payouts() == [
        Transfer(
            token=None,
            recipient=common_reward_data["buffer_accounting_target"],
            amount_wei=slippage,
        )
    ]

    # negative slippage gives overdraft
    slippage = -1
    test_datum = sample_record(common_reward_data, 0, slippage, 0)
    assert test_datum.is_overdraft()
    assert test_datum.as_payouts() == []


def test_reward_datum_0_0_1(common_reward_data):
    """Quote rewards only."""
    num_quotes = 1
    reward_per_quote = 6 * 10**18
    test_datum = sample_record(common_reward_data, 0, 0, num_quotes)
    assert not test_datum.is_overdraft()
    assert test_datum.as_payouts() == [
        Transfer(
            token=common_reward_data["cow_token"],
            recipient=common_reward_data["reward_target"],
            amount_wei=reward_per_quote * num_quotes,
        )
    ]


def test_reward_datum_4_1_0(common_reward_data):
    """COW payment for rewards, ETH payment for slippage."""
    primary_reward, slippage = 4, 1
    test_datum = sample_record(common_reward_data, primary_reward, slippage, 0)
    assert not test_datum.is_overdraft()
    assert test_datum.as_payouts() == [
        Transfer(
            token=None,
            recipient=common_reward_data["buffer_accounting_target"],
            amount_wei=slippage,
        ),
        Transfer(
            token=common_reward_data["cow_token"],
            recipient=common_reward_data["reward_target"],
            amount_wei=primary_reward * common_reward_data["conversion_rate"],
        ),
    ]


def test_reward_datum_slippage_reduces_reward(common_reward_data):
    """Negative slippage reduces COW reward."""
    primary_reward, slippage = 4, -1
    test_datum = sample_record(common_reward_data, primary_reward, slippage, 0)
    assert not test_datum.is_overdraft()
    assert test_datum.as_payouts() == [
        Transfer(
            token=common_reward_data["cow_token"],
            recipient=common_reward_data["reward_target"],
            amount_wei=(primary_reward + slippage)
            * common_reward_data["conversion_rate"],
        ),
    ]


def test_reward_datum_slippage_exceeds_reward(common_reward_data):
    """Negative slippage leads to overtraft."""
    primary_reward, slippage = 1, -4
    test_datum = sample_record(common_reward_data, primary_reward, slippage, 0)
    assert test_datum.is_overdraft()
    assert test_datum.as_payouts() == []


def test_reward_datum_reward_reduces_slippage(common_reward_data):
    """Negative reward  reduces ETH slippage payment."""
    primary_reward, slippage = -2, 3
    test_datum = sample_record(common_reward_data, primary_reward, slippage, 0)
    assert test_datum.total_outgoing_eth() == primary_reward + slippage
    assert test_datum.as_payouts() == [
        Transfer(
            token=None,
            recipient=common_reward_data["buffer_accounting_target"],
            amount_wei=test_datum.total_outgoing_eth(),
        ),
    ]


def test_performance_reward_service_fee(common_reward_data):
    """Sevice fee reduces COW reward."""
    primary_reward, num_quotes, service_fee = 100, 0, Fraction(15, 100)
    test_datum = sample_record(
        common_reward_data,
        primary_reward=primary_reward,
        slippage=0,
        num_quotes=num_quotes,
        service_fee=service_fee,
    )

    assert (
        test_datum.total_cow_reward()
        == test_datum.total_eth_reward() * common_reward_data["conversion_rate"]
    )  # ensure consistency of cow and eth batch rewards
    assert test_datum.total_service_fee() == int(
        primary_reward * common_reward_data["conversion_rate"] * service_fee
    )
    assert not test_datum.is_overdraft()
    assert test_datum.as_payouts() == [
        Transfer(
            token=common_reward_data["cow_token"],
            recipient=common_reward_data["reward_target"],
            amount_wei=int(primary_reward * (1 - service_fee))
            * common_reward_data["conversion_rate"],
        ),
    ]


def test_quote_reward_service_fee(common_reward_data):
    """Sevice fee reduces COW reward."""
    primary_reward, num_quotes, service_fee = 0, 100, Fraction(15, 100)
    reward_per_quote = 6 * 10**18

    test_datum = sample_record(
        common_reward_data,
        primary_reward=primary_reward,
        slippage=0,
        num_quotes=num_quotes,
        service_fee=service_fee,
    )

    assert test_datum.total_service_fee() == int(
        reward_per_quote * num_quotes * service_fee
    )  # only quote rewards enter

    assert not test_datum.is_overdraft()
    assert test_datum.as_payouts() == [
        Transfer(
            token=common_reward_data["cow_token"],
            recipient=common_reward_data["reward_target"],
            amount_wei=int(reward_per_quote * num_quotes * (1 - service_fee)),
        ),
    ]


def test_positive_reward_service_fee(common_reward_data):
    """Service fee reduces COW reward."""
    primary_reward = 10**18  # positive reward
    num_quotes = 100
    service_fee = Fraction(15, 100)
    reward_per_quote = 6 * 10**18

    test_datum = sample_record(
        common_reward_data,
        primary_reward=primary_reward,
        slippage=0,
        num_quotes=num_quotes,
        service_fee=service_fee,
    )

    assert test_datum.total_service_fee() == int(
        (
            primary_reward * common_reward_data["conversion_rate"]
            + reward_per_quote * num_quotes
        )
        * service_fee
    )

    assert not test_datum.is_overdraft()
    assert test_datum.as_payouts() == [
        Transfer(
            token=common_reward_data["cow_token"],
            recipient=common_reward_data["reward_target"],
            amount_wei=int(reward_per_quote * num_quotes * (1 - service_fee)),
        ),
        Transfer(
            token=common_reward_data["cow_token"],
            recipient=common_reward_data["reward_target"],
            amount_wei=int(
                primary_reward
                * common_reward_data["conversion_rate"]
                * (1 - service_fee)
            ),
        ),
    ]


def test_negative_reward_service_fee(common_reward_data):
    """Sevice fee reduces COW quote reward but not reduce a negative batch reward."""
    primary_reward = -(10**18)  # negative reward
    slippage = 2 * 10**18  # to avoid overdraft
    num_quotes = 100
    service_fee = Fraction(15, 100)
    reward_per_quote = 6 * 10**18
    test_datum = sample_record(
        common_reward_data,
        primary_reward=primary_reward,
        slippage=slippage,
        num_quotes=num_quotes,
        service_fee=service_fee,
    )

    assert (
        test_datum.total_cow_reward()
        == test_datum.total_eth_reward() * common_reward_data["conversion_rate"]
    )  # ensure consistency of cow and eth batch rewards
    assert test_datum.total_service_fee() == int(
        reward_per_quote * num_quotes * service_fee
    )  # only quote rewards enter

    assert not test_datum.is_overdraft()
    assert test_datum.as_payouts() == [
        Transfer(
            token=common_reward_data["cow_token"],
            recipient=common_reward_data["reward_target"],
            amount_wei=int(reward_per_quote * num_quotes * (1 - service_fee)),
        ),
        Transfer(
            token=None,
            recipient=common_reward_data["buffer_accounting_target"],
            amount_wei=slippage
            + primary_reward,  # no multiplication by 1 - service_fee
        ),
    ]
