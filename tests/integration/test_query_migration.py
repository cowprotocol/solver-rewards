import os
import unittest

from dune_client.client import DuneClient
from duneapi.api import DuneAPI

from src.fetch.dune import DuneFetcher
from src.models.accounting_period import AccountingPeriod
from src.queries import DuneVersion


class MyTestCase(unittest.TestCase):
    def setUp(self) -> None:
        self.dune_v1 = DuneAPI("", "")
        self.dune_v2 = DuneClient(os.environ["DUNE_API_KEY"])

    def test_similar_slippage(self):
        v1_fetcher = DuneFetcher(
            dune_v1=self.dune_v1,
            dune=self.dune_v2,
            period=AccountingPeriod("2022-11-01"),
        )
        v2_fetcher = DuneFetcher(
            dune_v1=self.dune_v1,
            dune=self.dune_v2,
            period=AccountingPeriod("2022-11-01"),
            dune_version=DuneVersion.V2,
        )
        # Takes about 2-3 minutes each. Could be parallelized!
        v1_slippage = v1_fetcher.get_period_slippage()
        v2_slippage = v2_fetcher.get_period_slippage()

        self.assertEqual(len(v1_slippage.negative), len(v2_slippage.negative))
        self.assertEqual(len(v1_slippage.positive), len(v2_slippage.positive))

        self.assertAlmostEqual(
            v1_slippage.sum_negative(), v2_slippage.sum_negative(), delta=1000
        )
        self.assertAlmostEqual(
            v1_slippage.sum_positive(), v2_slippage.sum_positive(), delta=1000
        )


if __name__ == "__main__":
    unittest.main()
