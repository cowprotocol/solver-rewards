import unittest

from duneapi.api import DuneAPI

from src.fetch.dune import DuneFetcher
from src.models.accounting_period import AccountingPeriod


class MyTestCase(unittest.TestCase):
    def setUp(self) -> None:
        self.dune = DuneFetcher(
            dune=DuneAPI.new_from_environment(), period=AccountingPeriod("2022-09-20")
        )

    def test_get_eth_spent(self):
        eth_transfers = self.dune.get_eth_spent()
        self.assertAlmostEqual(
            sum(t.amount_wei for t in eth_transfers),
            16745457506431162000,  # cf: https://dune.com/queries/1323288
            delta=5 * 10**4,  # WEI
        )

    def test_get_cow_rewards(self):
        self.dune.period = AccountingPeriod("2022-10-18", length_days=5)
        print(f"Check out results at: {self.dune.period.dashboard_url()}")
        try:
            self.dune.get_cow_rewards()
        except AssertionError as err:
            self.fail(f"get_cow_rewards failed with {err}")


if __name__ == "__main__":
    unittest.main()
