import os
import unittest
from pprint import pprint

import pytest
from dune_client.client import DuneClient
from dune_client.query import Query
from dune_client.types import QueryParameter

from src.fetch.dune import DuneFetcher
from src.models.accounting_period import AccountingPeriod
from src.models.slippage import SplitSlippages
from src.queries import QUERIES, DuneVersion
from tests.integration.common import exec_or_get


class TestDuneAnalytics(unittest.TestCase):
    def setUp(self) -> None:
        self.dune = DuneClient(os.environ["DUNE_API_KEY"])
        self.slippage_query = QUERIES["PERIOD_SLIPPAGE"]

    @staticmethod
    def slippage_query_for(period: AccountingPeriod, tx_hash: str) -> Query:
        return QUERIES["PERIOD_SLIPPAGE"].with_params(
            period.as_query_params()
            + [
                QueryParameter.text_type("TxHash", tx_hash),
                QueryParameter.text_type("CTE_NAME", "results_per_tx"),
            ]
        )

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
        period_slippage = SplitSlippages.from_data_set(fetcher.get_period_slippage())
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
        period = AccountingPeriod("2022-06-07", 1)
        query = QUERIES["PERIOD_SLIPPAGE"].with_params(
            period.as_query_params()
            + [QueryParameter.text_type("CTE_NAME", "results_per_tx")],
            dune_version=DuneVersion.V2,
        )
        results = exec_or_get(self.dune, query, result_id="01GW9SVRHYWWXV62R3FVZMQNEW")
        self.assertEqual(results.query_id, self.slippage_query.v2_query.query_id)
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
        results = exec_or_get(self.dune, query, result_id="01GW9SXZP72S2Z0TFWG6VCMTWS")
        self.assertEqual(results.query_id, self.slippage_query.v2_query.query_id)
        tx_slippage = results.get_rows()[0]
        self.assertEqual(tx_slippage["eth_slippage_wei"], 71151929005061256)
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
                QueryParameter.text_type("CTE_NAME", "results_per_tx"),
            ],
            dune_version=DuneVersion.V2,
        )
        results = exec_or_get(self.dune, query, result_id="01GW9T7R10PDK7P5SRNBM3Z8J2")
        self.assertEqual(results.query_id, self.slippage_query.v2_query.query_id)
        tx_slippage = results.get_rows()[0]
        self.assertEqual(tx_slippage["eth_slippage_wei"], 148427839329771600)
        self.assertAlmostEqual(
            tx_slippage["usd_value"], 177.37732880251593, delta=0.000000001
        )
        # When looking at the pure batch token imbalance:
        # https://dune.com/queries/1380984?TxHash=0x5c4e410ce5d741f60e06a8621c6f12839ad39273f5abf78d4bbc1cd3b31de46c
        # One sees 5 tokens listed. However, this calculation merges ETH/WETH together
        # as a single row one of those imbalances was excluded as an "internal trade"
        # https://dune.com/queries/1836718?CTE_NAME_e15077=final_token_balance_sheet&EndTime_d83555=2023-01-02+00%3A00%3A00&StartTime_d83555=2023-01-01+00%3A00%3A00&TxHash_t6c1ea=0x5c4e410ce5d741f60e06a8621c6f12839ad39273f5abf78d4bbc1cd3b31de46c
        self.assertEqual(tx_slippage["num_entries"], 4)

    def test_slippage_regression_1(self):
        """
        Two known batches with ETH transfers previously not captured.
        The following hashes were picked up by this query: https://dune.com/queries/1957339
        which displays batches where these missing ETH transfers occurred.
        Bug was picked up by our Dune Alerts on Feb. 2, 2023
        https://cowservices.slack.com/archives/C03PW4CR38A/p1675328564060139
        """
        period = AccountingPeriod("2023-02-01", 1)
        # Previously having -210 USD negative slippage.
        tx_hash = "0x3b2e9675b6d71a34e9b7f4abb4c9e80922be311076fcbb345d7da9d91a05e048"
        result_0x3b2e = exec_or_get(
            self.dune,
            query=self.slippage_query_for(period, tx_hash),
            result_id="01GW9T9X9EYRA48JYJKWMBQG4X",
        )
        self.assertEqual(result_0x3b2e.query_id, self.slippage_query.v2_query.query_id)
        self.assertEqual(
            result_0x3b2e.get_rows(),
            [
                {
                    "eth_slippage_wei": -4703808.820628837,
                    "hour": "2023-02-01 01:00:00.000 UTC",
                    "num_entries": 2,
                    "solver_address": "0xc9ec550bea1c64d779124b23a26292cc223327b6",
                    "tx_hash": tx_hash,
                    "usd_value": -7.454729493515833e-09,
                }
            ],
        )

    def test_slippage_regression_2(self):
        period = AccountingPeriod("2023-02-01", 1)
        # Previously having -150 USD slippage
        tx_hash = "0x7a007eb8ad25f5f1f1f36459998ae758b0e699ca69cc7b4c38354d42092651bf"
        result_0x7a00 = exec_or_get(
            self.dune,
            query=self.slippage_query_for(period, tx_hash),
            result_id="01GW9TAM3SJY5XP4DR0XB9SM24",
        )
        self.assertEqual(result_0x7a00.query_id, self.slippage_query.v2_query.query_id)
        self.assertEqual(
            result_0x7a00.get_rows(),
            [
                {
                    "eth_slippage_wei": -407937294.96877956,
                    "hour": "2023-02-01 01:00:00.000 UTC",
                    "num_entries": 3,
                    "solver_address": "0xc9ec550bea1c64d779124b23a26292cc223327b6",
                    "tx_hash": tx_hash,
                    "usd_value": -6.465105832898793e-07,
                }
            ],
        )


if __name__ == "__main__":
    unittest.main()
