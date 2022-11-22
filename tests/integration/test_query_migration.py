import os
import unittest

from dune_client.client import DuneClient
from duneapi.api import DuneAPI

from src.fetch.dune import DuneFetcher
from src.models.accounting_period import AccountingPeriod
from src.models.slippage import SolverSlippage, SplitSlippages
from src.queries import DuneVersion


class MyTestCase(unittest.TestCase):
    def setUp(self) -> None:
        self.dune_v1 = DuneAPI("", "")
        self.dune_v2 = DuneClient(os.environ["DUNE_API_KEY"])

    def test_similar_slippage(self):
        period = AccountingPeriod("2022-11-01", length_days=1)
        dune_v1 = self.dune_v1
        dune = self.dune_v2
        # These results expire at 2024-11-22
        # v1_result = dune.get_result("01GJGHR9AG3AAXCQSSGWFPRW5E")
        # v2_result = dune.get_result("01GJGHTRH14SSR33K7BK5RZ9B8")

        # v1_slippage = SplitSlippages.from_data_set(v1_result.get_rows())
        # v2_slippage = SplitSlippages.from_data_set(v2_result.get_rows())

        v1_fetcher = DuneFetcher(dune_v1, dune, period, dune_version=DuneVersion.V1)
        v2_fetcher = DuneFetcher(dune_v1, dune, period, dune_version=DuneVersion.V2)
        # Takes about 2-3 minutes each. Could be parallelized!
        v1_slippage = v1_fetcher.get_period_slippage()
        v2_slippage = v2_fetcher.get_period_slippage()

        print(v1_slippage)
        print(v2_slippage)

        self.assertAlmostEqual(
            v1_slippage.sum_negative(), v2_slippage.sum_negative(), delta=1000
        )
        self.assertAlmostEqual(
            v1_slippage.sum_positive(), v2_slippage.sum_positive(), delta=1000
        )


if __name__ == "__main__":
    unittest.main()
