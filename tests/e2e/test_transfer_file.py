import unittest
from datetime import datetime, timedelta

from duneapi.types import Address

from src.fetch.period_slippage import SolverSlippage
from src.fetch.transfer_file import Transfer, SplitTransfers, Overdraft
from src.models import AccountingPeriod
from src.utils.prices import eth_in_token, TokenId, token_in_eth, token_in_usd


class TestPrices(unittest.TestCase):
    def setUp(self) -> None:
        self.far_past = datetime.strptime("2022-01-01", "%Y-%m-%d")
        # https://api.coinpaprika.com/v1/tickers/cow-cow-protocol-token/historical?start=2022-01-01&interval=1d&end=2022-04-16
        self.first_cow_day = datetime.strptime("2022-04-15", "%Y-%m-%d")
        self.day_before_cow = self.first_cow_day - timedelta(days=1)

    def test_process_transfers(self):
        period = AccountingPeriod("2022-06-14")
        barn_zerox = Address("0xde786877a10dbb7eba25a4da65aecf47654f08ab")
        cow_token = Address("0xDEf1CA1fb7FBcDC777520aa7f396b4E015F497aB")
        mixed_transfers = [
            Transfer.native(
                receiver=barn_zerox,
                amount=0.18536027477313313,
            ),
            Transfer.erc20(receiver=barn_zerox, amount=600, token=cow_token),
        ]
        #  -0.32469736678953554

        slippage = SolverSlippage(
            amount_wei=-324697366789535540,
            solver_name="barn-0x",
            solver_address=barn_zerox,
        )
        indexed_slippage = {barn_zerox: slippage}
        cow_redirects = {}

        accounting = SplitTransfers(period, mixed_transfers)

        transfers = accounting.process(indexed_slippage, cow_redirects)
        # Both reimbursement and COW rewards were completely deducted.
        self.assertEqual(transfers, [])

        remaining_overdraft = accounting.overdrafts.get(barn_zerox)
        self.assertEqual(remaining_overdraft.eth, 0.09000226926318651)


if __name__ == "__main__":
    unittest.main()
