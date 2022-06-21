import unittest

from pprint import pprint

from duneapi.types import DuneQuery, QueryParameter, Network
from duneapi.util import open_query

from src.base_query import base_query
from src.fetch.period_slippage import QueryType
from src.models import AccountingPeriod
from tests.db.pg_client import (
    ConnectionType,
    DBRouter,
)


class TestDuneAnalytics(unittest.TestCase):
    def setUp(self) -> None:
        self.dune = DBRouter(ConnectionType.LOCAL)

    def tearDown(self) -> None:
        self.dune.close()

    def test_no_outrageous_slippage(self):
        """
        If numbers do not seem correct, the following script allows us to investigate
        which tx are having high slippage values in dollar terms
        """
        period = AccountingPeriod("2022-06-07", 1)
        query = base_query(
            name="Slippage Accounting",
            select=QueryType.PER_TX.select_statement(),
            period=period,
            connection_type=ConnectionType.LOCAL,
        )
        slippage_per_tx = self.dune.fetch(query)
        slippage_per_tx.sort(key=lambda t: int(t["eth_slippage_wei"]))

        top_five_negative = slippage_per_tx[:5]
        top_five_positive = slippage_per_tx[-5:]

        pprint(top_five_negative + top_five_positive)
        for obj in top_five_negative + top_five_positive:
            assert abs(int(obj["eth_slippage_wei"])) < 1 * 10**18


if __name__ == "__main__":
    unittest.main()
