import unittest

from dune_client.types import Address

from src.constants import COW_TOKEN_ADDRESS
from src.models.accounting_period import AccountingPeriod
from src.models.slippage import SolverSlippage
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


if __name__ == "__main__":
    unittest.main()
