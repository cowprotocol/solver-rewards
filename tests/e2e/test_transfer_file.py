import unittest

from dune_client.types import Address

from src.constants import COW_TOKEN_ADDRESS
from src.fetch.transfer_file import Transfer
from src.models.accounting_period import AccountingPeriod
from src.models.overdraft import Overdraft
from src.models.slippage import SolverSlippage
from src.models.split_transfers import SplitTransfers
from src.models.token import Token
from src.utils.print_store import PrintStore

ONE_ETH = 10**18


# TODO - mock the price feed so that this test doesn't require API call.
class TestPrices(unittest.TestCase):
    def test_process_transfers(self):
        period = AccountingPeriod("2022-06-14")
        barn_zerox = Address("0xde786877a10dbb7eba25a4da65aecf47654f08ab")
        other_solver = Address("0x" + "1" * 40)
        cow_token = Token(COW_TOKEN_ADDRESS)
        mixed_transfers = [
            Transfer(
                token=None,
                receiver=barn_zerox,
                amount_wei=185360274773133130,
            ),
            Transfer(token=None, receiver=other_solver, amount_wei=1 * ONE_ETH),
            Transfer(token=cow_token, receiver=barn_zerox, amount_wei=600 * ONE_ETH),
            Transfer(token=cow_token, receiver=other_solver, amount_wei=2000 * ONE_ETH),
        ]

        barn_slippage = SolverSlippage(
            amount_wei=-324697366789535540,
            solver_name="barn-0x",
            solver_address=barn_zerox,
        )
        other_slippage = SolverSlippage(
            amount_wei=-11 * 10**17,
            solver_name="Other Solver",
            solver_address=other_solver,
        )
        indexed_slippage = {barn_zerox: barn_slippage, other_solver: other_slippage}
        cow_redirects = {}

        accounting = SplitTransfers(period, mixed_transfers)

        transfers = accounting.process(indexed_slippage, cow_redirects, PrintStore())
        # The only remaining transfer is the other_solver's COW reward.
        self.assertEqual(
            transfers,
            [
                Transfer(
                    token=cow_token,
                    receiver=other_solver,
                    amount_wei=845094377028141056000,
                )
            ],
        )
        # barn_zerox still has outstanding overdraft
        self.assertEqual(
            accounting.overdrafts,
            {barn_zerox: Overdraft(period, barn_zerox, "barn-0x", 87384794957180304)},
        )
        # All unprocessed entries have been processed.
        self.assertEqual(accounting.unprocessed_cow, [])
        self.assertEqual(accounting.unprocessed_native, [])


if __name__ == "__main__":
    unittest.main()
