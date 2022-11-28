import os
import unittest
from pprint import pprint

import pytest
from dune_client.client import DuneClient
from dune_client.types import QueryParameter

from src.fetch.dune import DuneFetcher
from src.models.accounting_period import AccountingPeriod
from src.queries import QUERIES, DuneVersion
from tests.integration.common import exec_or_get


class TestDuneAnalytics(unittest.TestCase):
    def setUp(self) -> None:
        self.dune = DuneClient(os.environ["DUNE_API_KEY"])
        self.slippage_query = QUERIES["PERIOD_SLIPPAGE"]

    @pytest.mark.skip(
        reason="This takes a while to run and should probably be avoided without local testing."
    )
    def test_no_solver_has_huge_slippage_values(self):
        """
        This test makes sure that no solver had big slippage (bigger than 2 ETH).
        High slippage indicates that something significant is missing, but for sure
        I could happen that a solver has higher slippage than 2 ETH. In this case,
        there should be manual investigations
        """
        period = AccountingPeriod("2022-03-01", 1)
        fetcher = DuneFetcher(self.dune, period, DuneVersion.V2)
        period_slippage = fetcher.get_period_slippage()
        self.assertLess(
            period_slippage.sum_positive() - period_slippage.sum_negative(),
            2 * 10**18,
        )

    def test_no_outrageous_slippage(self):
        """
        If numbers do not seem correct, the following script allows us to investigate
        which tx are having high slippage values in dollar terms.
        This is unusual slippage.
        """
        dune = DuneClient(os.environ["DUNE_API_KEY"])
        period = AccountingPeriod("2022-06-07", 1)
        query = QUERIES["PERIOD_SLIPPAGE"].with_params(
            period.as_query_params()
            + [
                # Default values (on the query definition) do not need to be provided!
                # QueryParameter.text_type("TxHash", "0x")
                # QueryParameter.text_type("Solver", "0x")
                # QueryParameter.text_type("TokenList", ",".join(get_trusted_tokens())),
                QueryParameter.text_type("CTE_NAME", "results_per_tx")
            ],
            dune_version=DuneVersion.V2,
        )
        results = exec_or_get(dune, query, result_id="01GJX4SWHY7H20KPVPHCENEQRH")
        print(results.execution_id)
        slippage_per_tx = results.get_rows()

        slippage_per_tx.sort(key=lambda t: int(t["eth_slippage_wei"]))
        top_five_negative = slippage_per_tx[:5]
        top_five_positive = slippage_per_tx[-5:]

        pprint(top_five_negative + top_five_positive)
        for obj in top_five_negative + top_five_positive:
            assert abs(int(obj["eth_slippage_wei"])) < 1 * 10**18


if __name__ == "__main__":
    unittest.main()
