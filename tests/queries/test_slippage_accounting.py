import unittest

from duneapi.types import DuneQuery, Network, QueryParameter
from duneapi.util import open_query

from src.base_query import base_query
from src.fetch.period_slippage import SplitSlippages, QueryType
from src.models import AccountingPeriod
from tests.db.pg_client import ConnectionType, DBRouter


class TestDuneAnalytics(unittest.TestCase):
    def setUp(self) -> None:
        self.dune = DBRouter(ConnectionType.LOCAL)
        self.period = AccountingPeriod("2022-03-01", length_days=1)

    def tearDown(self) -> None:
        self.dune.close()

    def test_no_solver_has_huge_slippage_values(self):
        """
        This test makes sure that no solver had big slippage (bigger than 2 ETH).
        High slippage indicates that something significant is missing, but for sure
        I could happen that a solver has higher slippage than 2 ETH. In this case,
        there should be manual investigations
        """
        query = base_query(
            name="Slippage Accounting",
            select=QueryType.TOTAL.select_statement(),
            period=self.period,
            connection_type=ConnectionType.LOCAL,
        )
        local_query_results = self.dune.fetch(query)
        solver_slippages = SplitSlippages.from_data_set(data_set=local_query_results)
        self.assertLess(
            solver_slippages.sum_positive() - solver_slippages.sum_negative(),
            2 * 10**18,
        )


if __name__ == "__main__":
    unittest.main()
