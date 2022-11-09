import unittest

from duneapi.types import DuneQuery as LegacyDuneQuery, Network, QueryParameter

from src.models.slippage import (
    SplitSlippages,
    slippage_query,
)
from src.fetch.token_list import get_trusted_tokens
from src.models.accounting_period import AccountingPeriod
from tests.db.pg_client import ConnectionType, DBRouter


class TestDuneAnalytics(unittest.TestCase):
    def setUp(self) -> None:
        self.dune = DBRouter(ConnectionType.LOCAL)
        self.period = AccountingPeriod("2022-03-01", length_days=10)

    def tearDown(self) -> None:
        self.dune.close()

    def test_no_solver_has_huge_slippage_values(self):
        """
        This test makes sure that no solver had big slippage (bigger than 2 ETH).
        High slippage indicates that something significant is missing, but for sure
        I could happen that a solver has higher slippage than 2 ETH. In this case,
        there should be manual investigations
        """
        period = AccountingPeriod("2022-03-01", 1)
        query = LegacyDuneQuery(
            raw_sql=slippage_query(),
            network=Network.MAINNET,
            name="Slippage Accounting",
            parameters=[
                QueryParameter.date_type("StartTime", period.start),
                QueryParameter.date_type("EndTime", period.end),
                QueryParameter.text_type("TxHash", "0x"),
                QueryParameter.text_type("TokenList", ",".join(get_trusted_tokens())),
            ],
            description="",
            query_id=-1,
        )
        local_query_results = self.dune.fetch(query)
        solver_slippages = SplitSlippages.from_data_set(data_set=local_query_results)
        self.assertLess(
            solver_slippages.sum_positive() - solver_slippages.sum_negative(),
            2 * 10**18,
        )


if __name__ == "__main__":
    unittest.main()
