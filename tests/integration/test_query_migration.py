import os
import unittest

import pytest
from dune_client.client import DuneClient

from src.fetch.dune import DuneFetcher
from src.models.accounting_period import AccountingPeriod
from src.models.slippage import SplitSlippages
from src.models.transfer import Transfer
from src.queries import DuneVersion
from src.utils.dataset import index_by


class TestQueryMigration(unittest.TestCase):
    def setUp(self) -> None:
        self.dune = DuneClient(os.environ["DUNE_API_KEY"])
        period = AccountingPeriod("2022-11-01", length_days=7)
        self.v1_fetcher = DuneFetcher(
            dune=self.dune, period=period, dune_version=DuneVersion.V1
        )
        self.v2_fetcher = DuneFetcher(
            dune=self.dune, period=period, dune_version=DuneVersion.V2
        )

    def test_similar_slippage_cached_results_one_day(self):
        # These results expire at 2024-11-22
        v1_result = self.dune.get_result("01GJJBP5E0CE4XM8FJ7KBVB8KW")
        v2_result = self.dune.get_result("01GJJBNWMZNTTB6VQCFZMK7JCN")
        print(v1_result)
        print(v2_result)

        v1_slippage = SplitSlippages.from_data_set(v1_result.get_rows())
        v2_slippage = SplitSlippages.from_data_set(v2_result.get_rows())

        # v1_fetcher = DuneFetcher(dune_v1, dune, period, dune_version=DuneVersion.V1)
        # v2_fetcher = DuneFetcher(dune_v1, dune, period, dune_version=DuneVersion.V2)
        # # Takes about 2-3 minutes each. Could be parallelized!
        # v1_slippage = v1_fetcher.get_period_slippage()
        # v2_slippage = v2_fetcher.get_period_slippage()
        delta = 2  # decimal places ETH. This is 2.20 USD with ETH at 100
        self.assertAlmostEqual(
            v1_slippage.sum_negative() / 10**18,
            v2_slippage.sum_negative() / 10**18,
            delta,
        )
        self.assertAlmostEqual(
            v1_slippage.sum_positive() / 10**18,
            v2_slippage.sum_positive() / 10**18,
            delta,
        )

    @pytest.mark.skip(
        reason="This test takes FOREVER (~8m) to run, use the Cached version above."
    )
    def test_similar_slippage_for_period(self):
        # Takes about 2-3 minutes each. Could be parallelized!
        v1_slippage = self.v1_fetcher.get_period_slippage()
        v2_slippage = self.v2_fetcher.get_period_slippage()
        # Cached Results available at
        # V1: 01GJJD92TNQE0476SSWP2EMC34
        # V2: 01GJJDAZFKMNP7KKZWFWQKY05S

        delta = 2  # decimal places ETH. This is 2.20 USD with ETH at 100
        self.assertAlmostEqual(
            v1_slippage.sum_negative() / 10**18,
            v2_slippage.sum_negative() / 10**18,
            delta,
        )
        self.assertAlmostEqual(
            v1_slippage.sum_positive() / 10**18,
            v2_slippage.sum_positive() / 10**18,
            delta,
        )

    def test_identical_vouch_registry(self):
        v1_vouches = self.v1_fetcher.get_vouches()
        v2_vouches = self.v2_fetcher.get_vouches()

        self.assertEqual(v1_vouches, v2_vouches)

    def test_similar_eth_spent(self):
        v1_eth_spent = index_by(self.v1_fetcher.get_eth_spent(), "receiver")
        v2_eth_spent = index_by(self.v2_fetcher.get_eth_spent(), "receiver")
        # TODO - this Address class is more of a headache than benefit,
        #  we should just use validated strings
        cleaned_v1: dict[str, Transfer] = {
            a.address: v for a, v in v1_eth_spent.items()
        }
        cleaned_v2: dict[str, Transfer] = {
            a.address: v for a, v in v2_eth_spent.items()
        }

        self.assertEqual(set(cleaned_v1.keys()), set(cleaned_v2.keys()))
        for account in cleaned_v1.keys():  # They are equal, use either!
            v1 = cleaned_v1[account]
            v2 = cleaned_v2[account]
            # The values are accurate up to 12 decimal places!
            self.assertAlmostEqual(v1.amount, v2.amount, delta=12)
            # Even stronger is that they only differ by at most 10**4 WEI
            self.assertLess(abs(v1.amount_wei - v2.amount_wei), 10**4)

    def test_identical_risk_free_batches(self):
        self.assertEqual(
            self.v1_fetcher.get_risk_free_batches(),
            self.v2_fetcher.get_risk_free_batches(),
        )

    def test_identical_block_intervals(self):
        self.assertEqual(
            self.v1_fetcher.get_block_interval(), self.v2_fetcher.get_block_interval()
        )

    def test_identical_trade_counts(self):
        self.assertEqual(
            self.v1_fetcher.get_trade_counts(), self.v2_fetcher.get_trade_counts()
        )


if __name__ == "__main__":
    unittest.main()
