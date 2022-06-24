import unittest
from datetime import datetime, timedelta

from duneapi.types import Address

from src.fetch.period_slippage import SolverSlippage
from src.fetch.transfer_file import Transfer, SplitTransfers, Overdraft
from src.models import AccountingPeriod
from src.utils.prices import eth_in_token, TokenId, token_in_eth, token_in_usd


# TODO - mock the price feed so that this test doesn't require API call.
class TestPrices(unittest.TestCase):
    def setUp(self) -> None:
        self.far_past = datetime.strptime("2022-01-01", "%Y-%m-%d")
        # https://api.coinpaprika.com/v1/tickers/cow-cow-protocol-token/historical?start=2022-01-01&interval=1d&end=2022-04-16
        self.first_cow_day = datetime.strptime("2022-04-15", "%Y-%m-%d")
        self.day_before_cow = self.first_cow_day - timedelta(days=1)

    def test_process_transfers(self):
        period = AccountingPeriod("2022-06-14")
        barn_zerox = Address("0xde786877a10dbb7eba25a4da65aecf47654f08ab")
        other_solver = Address("0x" + "1" * 40)
        cow_token = Address("0xDEf1CA1fb7FBcDC777520aa7f396b4E015F497aB")
        mixed_transfers = [
            Transfer.native(
                receiver=barn_zerox,
                amount=0.18536027477313313,
            ),
            Transfer.native(receiver=other_solver, amount=1),
            Transfer.erc20(receiver=barn_zerox, amount=600, token=cow_token),
            Transfer.erc20(receiver=other_solver, amount=2000, token=cow_token),
        ]

        barn_slippage = SolverSlippage(
            amount_wei=-324697366789535540,
            solver_name="barn-0x",
            solver_address=barn_zerox,
        )
        other_slippage = SolverSlippage(
            amount_wei=-1100000000000000000,
            solver_name="Other Solver",
            solver_address=other_solver,
        )
        indexed_slippage = {barn_zerox: barn_slippage, other_solver: other_slippage}
        cow_redirects = {}

        accounting = SplitTransfers(period, mixed_transfers)

        transfers = accounting.process(indexed_slippage, cow_redirects)
        # The only remaining transfer is the other_solver's COW reward.
        self.assertEqual(
            transfers,
            [
                Transfer.erc20(
                    receiver=other_solver, token=cow_token, amount=783.8205013903926
                )
            ],
        )
        # barn_zerox still has outstanding overdraft
        self.assertEqual(
            accounting.overdrafts,
            {barn_zerox: Overdraft(period, barn_zerox, "barn-0x", 0.09000226926318651)},
        )
        # All unprocessed entries have been processed.
        self.assertEqual(accounting.unprocessed_cow, [])
        self.assertEqual(accounting.unprocessed_native, [])


if __name__ == "__main__":
    unittest.main()
