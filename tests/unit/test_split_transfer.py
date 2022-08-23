import unittest
from duneapi.types import Address

from src.constants import COW_TOKEN_ADDRESS
from src.fetch.period_slippage import SolverSlippage
from src.fetch.transfer_file import Transfer, SplitTransfers, Overdraft
from src.models import AccountingPeriod, Token
from duneapi.types import Address
from eth_typing import URI

ONE_ETH = 10**18


class TestSplitTransfers(unittest.TestCase):
    def test_process_native_transfers(self):
        class SplitTransfersTest(SplitTransfers):
            def __init__(
                self, period: AccountingPeriod, mixed_transfers: list[Transfer]
            ):
                SplitTransfers.__init__(self, period, mixed_transfers)

            def process_native_transfers(
                self, indexed_slippage: dict[Address, SolverSlippage]
            ) -> int:
                return SplitTransfers._process_native_transfers(self, indexed_slippage)

        period = AccountingPeriod("2022-06-14")
        barn_zerox = Address("0xde786877a10dbb7eba25a4da65aecf47654f08ab")
        cow_token = Token(COW_TOKEN_ADDRESS)
        mixed_transfers = [
            Transfer(
                token=None,
                receiver=barn_zerox,
                amount_wei=185360274773133130,
            ),
            Transfer(token=cow_token, receiver=barn_zerox, amount_wei=600 * ONE_ETH),
        ]

        barn_slippage = SolverSlippage(
            amount_wei=-195360274773133130,
            solver_name="barn-0x",
            solver_address=barn_zerox,
        )
        indexed_slippage = {barn_zerox: barn_slippage}
        accounting = SplitTransfersTest(period, mixed_transfers)

        total_penalty = accounting.process_native_transfers(indexed_slippage)
        expected_total_penality = -185360274773133130
        self.assertEqual(total_penalty, expected_total_penality)


if __name__ == "__main__":
    unittest.main()
