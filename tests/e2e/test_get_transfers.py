import os
import unittest

from dotenv import load_dotenv
from dune_client.client import DuneClient

from src.fetch.dune import DuneFetcher
from src.models.accounting_period import AccountingPeriod


class MyTestCase(unittest.TestCase):
    def setUp(self) -> None:
        load_dotenv()
        self.fetcher = DuneFetcher(
            DuneClient(os.environ["DUNE_API_KEY"]),
            AccountingPeriod("2022-10-18"),
        )

    def test_get_eth_spent(self):
        self.fetcher.period = AccountingPeriod("2022-09-20")
        eth_transfers = self.fetcher.get_eth_spent()
        self.assertAlmostEqual(
            sum(t.amount_wei for t in eth_transfers),
            16745457506431162000,  # cf: https://dune.com/queries/1323288
            delta=5 * 10**4,  # WEI
        )

    def test_get_cow_rewards(self):
        self.fetcher.period = AccountingPeriod("2022-10-18", length_days=5)
        print(f"Check out results at: {self.fetcher.period.dashboard_url()}")
        try:
            self.fetcher.get_cow_rewards()
        except AssertionError as err:
            self.fail(f"get_cow_rewards failed with {err}")


if __name__ == "__main__":
    unittest.main()
