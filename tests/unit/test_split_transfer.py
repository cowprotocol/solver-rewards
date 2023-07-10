import unittest

from dune_client.types import Address

from src.constants import COW_TOKEN_ADDRESS
from src.models.accounting_period import AccountingPeriod
from src.models.overdraft import Overdraft
from src.models.slippage import SolverSlippage, SplitSlippages
from src.models.split_transfers import SplitTransfers
from src.models.token import Token
from src.models.transfer import Transfer
from src.models.vouch import Vouch
from src.utils.print_store import PrintStore
from tests.unit.util_methods import redirected_transfer

ONE_ETH = 10**18


class TestSplitTransfers(unittest.TestCase):
    def setUp(self) -> None:
        self.period = AccountingPeriod("2023-06-14")
        self.solver = Address("0xde786877a10dbb7eba25a4da65aecf47654f08ab")
        self.solver_name = "solver_0"
        self.redirect_map = {
            self.solver: Vouch(
                solver=self.solver,
                reward_target=Address.from_int(2),
                bonding_pool=Address.from_int(3),
            )
        }
        self.cow_token = Token(COW_TOKEN_ADDRESS)

    def construct_split_transfers_and_process(
        self,
        solvers: list[Address],
        eth_amounts: list[int],
        cow_rewards: list[int],
        slippage_amounts: list[int],
        redirects: dict[Address, Vouch],
    ) -> SplitTransfers:
        eth_transfers = [
            Transfer(
                token=None,
                recipient=solvers[i],
                amount_wei=eth_amounts[i],
            )
            for i in range(len(solvers))
        ]
        cow_transfers = [
            Transfer(
                token=self.cow_token, recipient=solvers[i], amount_wei=cow_rewards[i]
            )
            for i in range(len(solvers))
        ]
        accounting = SplitTransfers(
            self.period,
            mixed_transfers=eth_transfers + cow_transfers,
            log_saver=PrintStore(),
        )
        accounting.process(
            slippages=SplitSlippages.from_data_set(
                [
                    {
                        "eth_slippage_wei": slippage_amounts[i],
                        "solver_address": solvers[i].address,
                        "solver_name": f"solver_{i}",
                    }
                    for i in range(len(slippage_amounts))
                ]
            ),
            cow_redirects=redirects,
        )
        return accounting

    def test_process_native_transfers(self):
        amount_of_transfer = 185360274773133130
        mixed_transfers = [
            Transfer(
                token=None,
                recipient=self.solver,
                amount_wei=amount_of_transfer,
            ),
            Transfer(
                token=self.cow_token, recipient=self.solver, amount_wei=600 * ONE_ETH
            ),
        ]

        slippage = SolverSlippage(
            amount_wei=-amount_of_transfer - ONE_ETH,
            solver_name=self.solver_name,
            solver_address=self.solver,
        )
        indexed_slippage = {self.solver: slippage}
        accounting = SplitTransfers(self.period, mixed_transfers, PrintStore())

        total_penalty = accounting._process_native_transfers(indexed_slippage)
        expected_total_penalty = -amount_of_transfer
        self.assertEqual(total_penalty, expected_total_penalty)

    def test_process_rewards(self):
        cow_reward = 600 * ONE_ETH
        mixed_transfers = [
            Transfer(
                token=self.cow_token, recipient=self.solver, amount_wei=cow_reward
            ),
        ]
        accounting = SplitTransfers(self.period, mixed_transfers, PrintStore())
        reward_target = Address.from_int(7)
        redirect_map = {
            self.solver: Vouch(
                solver=self.solver,
                reward_target=reward_target,
                bonding_pool=Address.zero(),
            )
        }
        slippage_amount = 1
        positive_slippage = [
            SolverSlippage(
                amount_wei=slippage_amount, solver_address=self.solver, solver_name=""
            )
        ]
        accounting._process_rewards(redirect_map, positive_slippage)
        # Although we haven't called process_native_transfers, we are appending positive slippage inside
        self.assertEqual(
            accounting.eth_transfers,
            [
                redirected_transfer(
                    token=None,
                    recipient=self.solver,
                    amount_wei=slippage_amount,
                    redirect=redirect_map[self.solver].reward_target,
                )
            ],
        )
        self.assertEqual(
            accounting.cow_transfers,
            [
                redirected_transfer(
                    token=self.cow_token,
                    recipient=self.solver,
                    amount_wei=cow_reward,
                    redirect=redirect_map[self.solver].reward_target,
                )
            ],
        )

    def test_full_process_with_positive_slippage(self):
        eth_amount = 2 * ONE_ETH
        cow_reward = 600 * ONE_ETH
        slippage_amount = 1 * ONE_ETH
        accounting = self.construct_split_transfers_and_process(
            solvers=[self.solver],
            eth_amounts=[eth_amount],
            cow_rewards=[cow_reward],
            slippage_amounts=[slippage_amount],
            redirects=self.redirect_map,
        )

        self.assertEqual(
            accounting.eth_transfers,
            [
                # The ETH Spent
                Transfer(
                    token=None,
                    recipient=self.solver,
                    amount_wei=eth_amount,
                ),
                # The redirected positive slippage
                redirected_transfer(
                    token=None,
                    recipient=self.solver,
                    amount_wei=slippage_amount,
                    redirect=self.redirect_map[self.solver].reward_target,
                ),
            ],
        )
        self.assertEqual(
            accounting.cow_transfers,
            [
                redirected_transfer(
                    token=self.cow_token,
                    recipient=self.solver,
                    amount_wei=cow_reward,
                    redirect=self.redirect_map[self.solver].reward_target,
                ),
            ],
        )
        self.assertEqual(accounting.unprocessed_cow, [])
        self.assertEqual(accounting.unprocessed_native, [])

    def test_process_with_negative_slippage_not_exceeding_eth(self):
        eth_amount = 2 * ONE_ETH
        cow_reward = 600 * ONE_ETH
        slippage_amount = -1 * ONE_ETH
        accounting = self.construct_split_transfers_and_process(
            solvers=[self.solver],
            eth_amounts=[eth_amount],
            cow_rewards=[cow_reward],
            slippage_amounts=[slippage_amount],
            redirects=self.redirect_map,
        )

        self.assertEqual(
            accounting.eth_transfers,
            [
                Transfer(
                    token=None,
                    recipient=self.solver,
                    # Slippage is negative (so it is added here)
                    amount_wei=eth_amount + slippage_amount,
                ),
            ],
        )
        self.assertEqual(
            accounting.cow_transfers,
            [
                redirected_transfer(
                    token=self.cow_token,
                    recipient=self.solver,
                    amount_wei=cow_reward,
                    redirect=self.redirect_map[self.solver].reward_target,
                ),
            ],
        )
        self.assertEqual(accounting.unprocessed_cow, [])
        self.assertEqual(accounting.unprocessed_native, [])

    @unittest.mock.patch('src.models.split_transfers.token_in_eth')
    def test_process_with_overdraft_exceeding_eth_not_cow(self, mock_token_in_eth):
        eth_amount = 2 * ONE_ETH
        cow_reward = 100_000 * ONE_ETH  # This is huge so COW is not exceeded!
        slippage_amount = -3 * ONE_ETH
        accounting = self.construct_split_transfers_and_process(
            solvers=[self.solver],
            eth_amounts=[eth_amount],
            cow_rewards=[cow_reward],
            slippage_amounts=[slippage_amount],
            redirects=self.redirect_map,
        )

        # Configure the mock to return the desired value
        cow_deduction = cow_reward - 25369802491025623613440
        mock_token_in_eth.return_value = cow_deduction

        self.assertEqual(
            accounting.eth_transfers,
            [],
            "No ETH reimbursement! when slippage exceeds eth_spent",
        )
        self.assertEqual(
            accounting.cow_transfers,
            [
                redirected_transfer(
                    token=self.cow_token,
                    recipient=self.solver,
                    # This is the amount of COW deducted based on a "deterministic" price
                    # on the date of the fixed accounting period.
                    amount_wei=cow_reward - 25369802491025623613440,
                    redirect=self.redirect_map[self.solver].reward_target,
                )
            ],
        )
        self.assertEqual(accounting.unprocessed_cow, [])
        self.assertEqual(accounting.unprocessed_native, [])

    def test_process_with_overdraft_exceeding_both_eth_and_cow(self):
        eth_amount = 1 * ONE_ETH
        cow_reward = 1000 * ONE_ETH
        slippage_amount = -3 * ONE_ETH

        accounting = self.construct_split_transfers_and_process(
            solvers=[self.solver],
            eth_amounts=[eth_amount],
            cow_rewards=[cow_reward],
            slippage_amounts=[slippage_amount],
            redirects=self.redirect_map,
        )
        # Solver get no ETH reimbursement and no COW tokens
        self.assertEqual(accounting.eth_transfers, [])
        self.assertEqual(accounting.cow_transfers, [])
        # Additional overdraft appended to overdrafts.
        self.assertEqual(
            accounting.overdrafts,
            {
                self.solver: Overdraft(
                    period=self.period,
                    account=self.solver,
                    name=self.solver_name,
                    wei=1960583059314169344,
                )
            },
        )
        self.assertEqual(accounting.unprocessed_cow, [])
        self.assertEqual(accounting.unprocessed_native, [])

    def test_process_with_missing_redirect(self):
        """
        Solver has 1 ETH of positive slippage and COW reward but no redirect address is supplied.
        The solver itself should receive 2 ETH transfers + 1 COW transfer.
        Note that the 2 ETH transfers get "consolidated" (or squashed) in to
        one only later in the process via `Transfer.consolidate`
        """

        eth_amount = 1 * ONE_ETH
        cow_reward = 100 * ONE_ETH
        slippage_amount = 1 * ONE_ETH
        accounting = self.construct_split_transfers_and_process(
            solvers=[self.solver],
            eth_amounts=[eth_amount],
            cow_rewards=[cow_reward],
            slippage_amounts=[slippage_amount],
            redirects={},  # Note the empty Redirect mapping!
        )

        self.assertEqual(
            accounting.eth_transfers,
            [
                Transfer(
                    token=None,
                    recipient=self.solver,
                    amount_wei=eth_amount,
                ),
                Transfer(
                    token=None,
                    recipient=self.solver,
                    amount_wei=slippage_amount,
                ),
            ],
        )
        self.assertEqual(
            accounting.cow_transfers,
            [
                Transfer(
                    token=self.cow_token,
                    recipient=self.solver,
                    amount_wei=cow_reward,
                ),
            ],
        )
        self.assertEqual(accounting.unprocessed_cow, [])
        self.assertEqual(accounting.unprocessed_native, [])

        # Just for info, but not relevant to this test - demonstrating that these transfers are squashed.
        consolidated_transfers = Transfer.consolidate(accounting.eth_transfers)
        self.assertEqual(len(consolidated_transfers), 1)
        self.assertEqual(
            consolidated_transfers[0].amount_wei, eth_amount + slippage_amount
        )

    def test_process_multiple_solver_same_reward_target(self):
        """
        Two solvers having their eth reimbursement sent to themselves,
        but COW rewards going to the same target.
        """
        solvers = [Address.from_int(1), Address.from_int(2)]
        reward_target = Address.from_int(3)
        eth_amounts = [1 * ONE_ETH, 2 * ONE_ETH]
        cow_rewards = [100 * ONE_ETH, 200 * ONE_ETH]
        accounting = self.construct_split_transfers_and_process(
            solvers,
            eth_amounts,
            cow_rewards,
            slippage_amounts=[],
            redirects={
                solvers[0]: Vouch(
                    solver=solvers[0],
                    reward_target=reward_target,
                    bonding_pool=Address.zero(),
                ),
                solvers[1]: Vouch(
                    solver=solvers[1],
                    reward_target=reward_target,
                    bonding_pool=Address.zero(),
                ),
            },
        )

        self.assertEqual(
            accounting.eth_transfers,
            [
                Transfer(
                    token=None,
                    recipient=solvers[0],
                    amount_wei=eth_amounts[0],
                ),
                Transfer(
                    token=None,
                    recipient=solvers[1],
                    amount_wei=eth_amounts[1],
                ),
            ],
        )
        self.assertEqual(
            accounting.cow_transfers,
            [
                redirected_transfer(
                    token=self.cow_token,
                    recipient=solvers[0],
                    amount_wei=cow_rewards[0],
                    redirect=reward_target,
                ),
                redirected_transfer(
                    token=self.cow_token,
                    recipient=solvers[1],
                    amount_wei=cow_rewards[1],
                    redirect=reward_target,
                ),
            ],
        )
        self.assertEqual(accounting.unprocessed_cow, [])
        self.assertEqual(accounting.unprocessed_native, [])


if __name__ == "__main__":
    unittest.main()
