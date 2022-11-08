import unittest

from pprint import pprint

from duneapi.types import DuneQuery, QueryParameter, Network

from src.fetch.period_slippage import QueryType, slippage_query
from src.fetch.token_list import fetch_trusted_tokens
from src.models.accounting_period import AccountingPeriod
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
        slippage_per_tx = self.dune.fetch(
            DuneQuery(
                raw_sql=slippage_query(QueryType.PER_TX),
                network=Network.MAINNET,
                name="Slippage Accounting",
                parameters=[
                    QueryParameter.date_type("StartTime", period.start),
                    QueryParameter.date_type("EndTime", period.end),
                    QueryParameter.text_type("TxHash", "0x"),
                    QueryParameter.text_type(
                        "TokenList", ",".join(fetch_trusted_tokens())
                    ),
                ],
                description="",
                query_id=-1,
            )
        )
        slippage_per_tx.sort(key=lambda t: int(t["eth_slippage_wei"]))

        top_five_negative = slippage_per_tx[:5]
        top_five_positive = slippage_per_tx[-5:]

        pprint(top_five_negative + top_five_positive)
        for obj in top_five_negative + top_five_positive:
            assert abs(int(obj["eth_slippage_wei"])) < 1 * 10**18


if __name__ == "__main__":
    unittest.main()
