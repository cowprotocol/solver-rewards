import os
import unittest
from pprint import pprint

import pytest
from dune_client.client import DuneClient
from dune_client.types import QueryParameter

from compute.src.fetch.dune import DuneFetcher
from compute.src.models.accounting_period import AccountingPeriod
from compute.src.queries import QUERIES, DuneVersion
from compute.tests.integration.common import exec_or_get


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

    def test_simple_positive_slippage(self):
        """
        Transaction 0x2509839cda8a4fec0c3b0ae4e90537aef5afaaeeee88427161d1b08367aeb0d7
        contains a single UniV3 interaction and resulted in 82 USDC positive slippage.
        """
        period = AccountingPeriod("2022-12-16", 1)
        query = QUERIES["PERIOD_SLIPPAGE"].with_params(
            period.as_query_params()
            + [
                # Default values (on the query definition) do not need to be provided!
                QueryParameter.text_type(
                    "TxHash",
                    "0x2509839cda8a4fec0c3b0ae4e90537aef5afaaeeee88427161d1b08367aeb0d7",
                ),
                QueryParameter.text_type("CTE_NAME", "results_per_tx"),
            ],
            dune_version=DuneVersion.V2,
        )
        results = exec_or_get(self.dune, query, result_id="01GP3A0QV1BNWF55Z5N362RK8M")
        tx_slippage = results.get_rows()[0]
        self.assertEqual(tx_slippage["eth_slippage_wei"], 71151929005056890)
        self.assertAlmostEqual(
            tx_slippage["usd_value"], 83.37280645114296, delta=0.00001
        )

    def test_positive_slippage_evaluation(self):
        """
        Transaction 0x5c4e410ce5d741f60e06a8621c6f12839ad39273f5abf78d4bbc1cd3b31de46c
        Alerted on January 1, 2023.
        https://dune.com/queries/1688044?MinAbsoluteSlippageTolerance=100&TxHash=0x&RelativeSlippageTolerance=1.0&SignificantSlippageValue=2000&StartTime=2023-01-01+00%3A00%3A00&EndTime=2023-01-02+00%3A00%3A00&EndTime_d83555=2023-01-02+00%3A00%3A00&MinAbsoluteSlippageTolerance_n26d66=100&RelativeSlippageTolerance_n26d66=1.0&SignificantSlippageValue_n26d66=2000&StartTime_d83555=2023-01-01+00%3A00%3A00&TxHash_t6c1ea=0x
        """
        period = AccountingPeriod("2023-01-01", 1)
        query = QUERIES["PERIOD_SLIPPAGE"].with_params(
            period.as_query_params()
            + [
                # Default values (on the query definition) do not need to be provided!
                QueryParameter.text_type(
                    "TxHash",
                    "0x5c4e410ce5d741f60e06a8621c6f12839ad39273f5abf78d4bbc1cd3b31de46c",
                ),
                # QueryParameter.text_type("SolverAddress", "0x97ec0a17432d71a3234ef7173c6b48a2c0940896"),
                # QueryParameter.text_type("TokenList", ",".join(get_trusted_tokens())),
                QueryParameter.text_type("CTE_NAME", "results_per_tx"),
            ],
            dune_version=DuneVersion.V2,
        )
        results = exec_or_get(self.dune, query, result_id="01GP11D7FH4WAEFW1Z46Q79VBC")
        tx_slippage = results.get_rows()[0]
        self.assertEqual(tx_slippage["eth_slippage_wei"], 148427839329771300)
        self.assertAlmostEqual(
            tx_slippage["usd_value"], 177.37732880251593, delta=0.000000001
        )
        # When looking at the pure batch token imbalance:
        # https://dune.com/queries/1380984?TxHash=0x5c4e410ce5d741f60e06a8621c6f12839ad39273f5abf78d4bbc1cd3b31de46c
        # One sees 5 tokens listed. However, this calculation merges ETH/WETH together
        # as a single row one of those imbalances was excluded as an "internal trade"
        # https://dune.com/queries/1836718?CTE_NAME_e15077=final_token_balance_sheet&EndTime_d83555=2023-01-02+00%3A00%3A00&StartTime_d83555=2023-01-01+00%3A00%3A00&TxHash_t6c1ea=0x5c4e410ce5d741f60e06a8621c6f12839ad39273f5abf78d4bbc1cd3b31de46c
        self.assertEqual(tx_slippage["num_entries"], 4)


if __name__ == "__main__":
    unittest.main()
