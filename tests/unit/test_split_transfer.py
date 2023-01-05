import unittest

from dune_client.types import Address

from src.constants import COW_TOKEN_ADDRESS
from src.models.accounting_period import AccountingPeriod
from src.models.slippage import SolverSlippage, SplitSlippages
from src.models.split_transfers import SplitTransfers
from src.models.token import Token
from src.models.transfer import Transfer
from src.models.vouch import Vouch
from src.utils.print_store import PrintStore

ONE_ETH = 10**18


class TestSplitTransfers(unittest.TestCase):
    def setUp(self) -> None:
        self.period = AccountingPeriod("2022-06-14")
        self.solver = Address("0xde786877a10dbb7eba25a4da65aecf47654f08ab")
        self.solver_name = "barn-0x"
        self.cow_token = Token(COW_TOKEN_ADDRESS)

    def test_process_native_transfers(self):
        amount_of_transfer = 185360274773133130
        mixed_transfers = [
            Transfer(
                token=None,
                receiver=self.solver,
                amount_wei=amount_of_transfer,
            ),
            Transfer(
                token=self.cow_token, receiver=self.solver, amount_wei=600 * ONE_ETH
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
            Transfer(token=self.cow_token, receiver=self.solver, amount_wei=cow_reward),
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
                Transfer(
                    token=None,
                    receiver=redirect_map[self.solver].reward_target,
                    amount_wei=slippage_amount,
                )
            ],
        )
        self.assertEqual(
            accounting.cow_transfers,
            [
                Transfer(
                    token=self.cow_token,
                    receiver=redirect_map[self.solver].reward_target,
                    amount_wei=cow_reward,
                )
            ],
        )

    def test_full_process(self):
        """
        This scenario involves two solvers, one with positive and one with negative slippage.
        The negative slippage does not involve any overdraft!
        All amounts (execution costs, cow rewards and slippage) are declared at the top of the test.
        The expected outcome is
        - 3 ETH transfers:
            - 2 for execution costs with one having negative slippage deducted.
            - 1 for positive slippage (redirected to the reward target)
        - 2 COW transfers (one for each solver).
        """
        solvers = [
            Address.from_int(1),
            Address.from_int(2),
        ]
        eth_amounts = [
            2 * ONE_ETH,
            3 * ONE_ETH,
        ]
        cow_rewards = [
            600 * ONE_ETH,
            100 * ONE_ETH,
        ]
        slippage_amounts = [
            1 * ONE_ETH,
            -1 * ONE_ETH,
        ]

        accounting = SplitTransfers(
            self.period,
            mixed_transfers=[
                Transfer(
                    token=None,
                    receiver=solvers[0],
                    amount_wei=eth_amounts[0],
                ),
                Transfer(
                    token=None,
                    receiver=solvers[1],
                    amount_wei=eth_amounts[1],
                ),
                Transfer(
                    token=self.cow_token, receiver=solvers[0], amount_wei=cow_rewards[0]
                ),
                Transfer(
                    token=self.cow_token, receiver=solvers[1], amount_wei=cow_rewards[1]
                ),
            ],
            log_saver=PrintStore(),
        )
        reward_targets = [
            Address.from_int(3),
            Address.from_int(4),
        ]
        redirect_map = {
            solvers[0]: Vouch(
                solver=solvers[0],
                reward_target=reward_targets[0],
                bonding_pool=Address.zero(),
            ),
            solvers[1]: Vouch(
                solver=solvers[1],
                reward_target=reward_targets[1],
                bonding_pool=Address.zero(),
            ),
        }
        accounting.process(
            slippage=SplitSlippages.from_data_set(
                [
                    {
                        "eth_slippage_wei": slippage_amounts[0],
                        "solver_address": solvers[0].address,
                        "solver_name": "irrelevant1",
                    },
                    {
                        "eth_slippage_wei": slippage_amounts[1],
                        "solver_address": solvers[1].address,
                        "solver_name": "irrelevant2",
                    },
                ]
            ),
            cow_redirects=redirect_map,
        )
        # Although we haven't called process_native_transfers, we are appending positive slippage inside
        self.assertEqual(
            accounting.eth_transfers,
            [
                Transfer(
                    token=None,
                    receiver=solvers[0],
                    amount_wei=eth_amounts[0],
                ),
                Transfer(
                    token=None,
                    receiver=solvers[1],
                    # Slippage is negative (so it is added here)
                    amount_wei=eth_amounts[1] + slippage_amounts[1],
                ),
                Transfer(
                    token=None,
                    # The solver with positive slippage!
                    receiver=redirect_map[solvers[0]].reward_target,
                    amount_wei=slippage_amounts[0],
                ),
            ],
        )
        self.assertEqual(
            accounting.cow_transfers,
            [
                Transfer(
                    token=self.cow_token,
                    receiver=redirect_map[solvers[0]].reward_target,
                    amount_wei=cow_rewards[0],
                ),
                Transfer(
                    token=self.cow_token,
                    receiver=redirect_map[solvers[1]].reward_target,
                    amount_wei=cow_rewards[1],
                ),
            ],
        )


if __name__ == "__main__":
    unittest.main()
