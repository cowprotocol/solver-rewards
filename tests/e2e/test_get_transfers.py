import unittest

from duneapi.api import DuneAPI
from duneapi.types import DuneQuery, QueryParameter, Network
from duneapi.util import open_query

from src.fetch.transfer_file import (
    get_transfers,
    get_cow_rewards,
    get_eth_spent,
    COW_PER_BATCH,
    COW_PER_TRADE,
    Transfer,
)
from src.models import AccountingPeriod


class MyTestCase(unittest.TestCase):
    def setUp(self) -> None:
        self.dune = DuneAPI.new_from_environment()
        self.period = AccountingPeriod("2022-09-20")

    def test_get_eth_spent(self):
        eth_transfers = get_eth_spent(self.dune, self.period)
        self.assertAlmostEqual(
            sum(t.amount for t in eth_transfers),
            16.745457506431146000,  # cf: https://dune.com/queries/1323288
            delta=0.0000000000001,
        )

    def test_get_cow_rewards(self):
        start_block, end_block = self.period.get_block_interval(self.dune)
        cow_transfers = get_cow_rewards(start_block, end_block)
        dune_results = self.dune.fetch(
            query=DuneQuery.from_environment(
                raw_sql=open_query("./tests/queries/dune_cow_rewards.sql"),
                name="COW Rewards",
                network=Network.MAINNET,
                parameters=[
                    QueryParameter.date_type("StartTime", self.period.start),
                    QueryParameter.date_type("EndTime", self.period.end),
                    QueryParameter.number_type("PerBatchReward", COW_PER_BATCH),
                    QueryParameter.number_type("PerTradeReward", COW_PER_TRADE),
                ],
            )
        )
        expected_results = [Transfer.from_dict(d) for d in dune_results]
        self.assertAlmostEqual(
            sum(ct.amount_wei for ct in cow_transfers),
            sum(t.amount_wei for t in expected_results),
        )


if __name__ == "__main__":
    unittest.main()
