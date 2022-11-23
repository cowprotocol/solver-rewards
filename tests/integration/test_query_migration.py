import os
import unittest

import pytest
from dune_client.client import DuneClient
from duneapi.api import DuneAPI

from src.fetch.dune import DuneFetcher
from src.models.accounting_period import AccountingPeriod
from src.models.slippage import SolverSlippage, SplitSlippages
from src.queries import DuneVersion


class TestQueryMigration(unittest.TestCase):
    def setUp(self) -> None:
        self.dune_v1 = DuneAPI("", "")
        self.dune_v2 = DuneClient(os.environ["DUNE_API_KEY"])

    def test_similar_slippage_cached_results_one_day(self):
        period = AccountingPeriod("2022-11-01", length_days=1)
        dune_v1 = self.dune_v1
        dune = self.dune_v2
        # These results expire at 2024-11-22
        v1_result = dune.get_result("01GJJBP5E0CE4XM8FJ7KBVB8KW")
        v2_result = dune.get_result("01GJJBNWMZNTTB6VQCFZMK7JCN")
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
        reason="This test takes FOREVER to run, use the Cached version above."
    )
    def test_similar_slippage_for_period(self):
        period = AccountingPeriod("2022-11-01", length_days=1)
        dune_v1 = self.dune_v1
        dune = self.dune_v2

        v1_fetcher = DuneFetcher(dune_v1, dune, period, dune_version=DuneVersion.V1)
        v2_fetcher = DuneFetcher(dune_v1, dune, period, dune_version=DuneVersion.V2)
        # Takes about 2-3 minutes each. Could be parallelized!
        v1_slippage = v1_fetcher.get_period_slippage()
        v2_slippage = v2_fetcher.get_period_slippage()
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


if __name__ == "__main__":
    unittest.main()
