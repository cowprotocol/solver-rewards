import os
import unittest

from dune_client.client import DuneClient

from compute.src.fetch.dune import DuneFetcher
from compute.src.models.accounting_period import AccountingPeriod
from compute.src.models.transfer import Transfer
from compute.src.queries import DuneVersion
from compute.src.utils.dataset import index_by


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
