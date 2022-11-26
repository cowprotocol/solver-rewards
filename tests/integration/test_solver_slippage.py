import json
import os
import unittest
from collections import defaultdict
from dataclasses import dataclass
from typing import Optional

import pytest
from dune_client.client import DuneClient
from dune_client.query import Query
from dune_client.file.interface import FileIO
from dune_client.types import QueryParameter

from src.constants import FILE_OUT_DIR
from src.fetch.dune import DuneFetcher
from src.models.accounting_period import AccountingPeriod
from src.models.slippage import SplitSlippages
from src.queries import QUERIES, DuneVersion


@dataclass
class Comparison:
    v1: dict[str, list]
    v2: dict[str, list]
    v1_not_v2: set[str]
    v2_not_v1: set[str]
    overlap: set[str]

    @classmethod
    def from_dune_results(
        cls, v1_result: list[dict[str, str]], v2_result: list[dict[str, str]]
    ):
        v1, v2 = defaultdict(list), defaultdict(list)
        while v1_result:
            row = v1_result.pop()
            v1[row["tx_hash"].replace("\\x", "0x")].append(row)

        while v2_result:
            row = v2_result.pop()
            v2[row["tx_hash"]].append(row)

        return cls(
            v1=v1,
            v2=v2,
            v1_not_v2=set(v1.keys()) - set(v2.keys()),
            v2_not_v1=set(v2.keys()) - set(v1.keys()),
            overlap=set(v2.keys()).intersection(set(v1.keys())),
        )

    def __str__(self):
        return (
            f"v1_not_v2={len(self.v1_not_v2)}\n"
            f"v2_not_v1={len(self.v2_not_v1)}\n"
            f"overlap={len(self.overlap)}"
        )

    def to_json(self, tx_hash: str):
        return json.dumps({"V1": self.v1[tx_hash], "V2": self.v2[tx_hash]})


class TestQueryMigration(unittest.TestCase):
    def setUp(self) -> None:
        self.dune = DuneClient(os.environ["DUNE_API_KEY"])
        self.period = AccountingPeriod("2022-11-01", length_days=7)
        self.slippage_query = QUERIES["PERIOD_SLIPPAGE"]
        self.parameters = self.period.as_query_params()
        self.writer = FileIO(FILE_OUT_DIR)

    def exec_or_get(self, query: Query, result_id: Optional[str] = None):
        if not result_id:
            return self.dune.refresh(query)
        return self.dune.get_result(result_id)

    def get_cte_rows(
        self,
        cte_name: str,
        tx_hash: Optional[str] = None,
        v1_cache: Optional[str] = None,
        v2_cache: Optional[str] = None,
    ):
        parameters = self.period.as_query_params()
        parameters.append(QueryParameter.enum_type("CTE_NAME", cte_name))
        if tx_hash:
            parameters.append(QueryParameter.text_type("TxHash", tx_hash))

        v1_results = self.exec_or_get(Query(1570227, params=parameters), v1_cache)
        v2_results = self.exec_or_get(Query(1570561, params=parameters), v2_cache)

        v1_rows = v1_results.get_rows()
        v2_rows = v2_results.get_rows()
        return v1_rows, v2_rows

    def get_cte_results(
        self,
        cte_name: str,
        tx_hash: Optional[str] = None,
        v1_cache: Optional[str] = None,
        v2_cache: Optional[str] = None,
    ):
        v1_rows, v2_rows = self.get_cte_rows(cte_name, tx_hash, v1_cache, v2_cache)
        self.writer.write_csv(v1_rows, f"{cte_name}_{tx_hash}_v1.csv")
        self.writer.write_csv(v2_rows, f"{cte_name}_{tx_hash}_v2.csv")
        return Comparison.from_dune_results(v1_rows, v2_rows)

    def test_batch_transfers(self):
        table_name = "batch_transfers"
        data = self.get_cte_results(
            table_name,
            v1_cache="01GJQNSER0PYSMGHMEBDT03805",
            v2_cache="01GJQNSER0PYSMGHMEBDT03805",
        )

        # No missing transactions.
        self.assertEqual(data.v2_not_v1, set())
        self.assertEqual(data.v1_not_v2, set())

        for tx_hash in data.overlap:
            x = data.v1[tx_hash]
            y = data.v2[tx_hash]
            self.assertEqual(
                len(x),
                len(y),
                f"{table_name} failed at {tx_hash} on\n {data.to_json(tx_hash)}",
            )

    def test_incoming_and_outgoing(self):
        # This test demonstrates that records are "essentially" matching up to this table.
        table_name = "incoming_and_outgoing"
        data = self.get_cte_results(
            table_name,
            # v1_cache="01GJR1HKR37V7HRPTRJCDMZBAX",
            # v2_cache="01GJR1HTNS87RKTV90WKH4TVSC",
        )

        # There are 14 records in missing_v2 for the specified accounting period.
        # This appears to be due to the estimated dex_swaps (in v1 are 0, but in v2 check)
        # https://dune.com/queries/1655081?CTE_NAME=batch_data&TxHash={TxHash}
        missing_v2 = {k: v for k, v in data.v1.items() if k in data.v1_not_v2}
        missing_v1 = {k: v for k, v in data.v2.items() if k in data.v2_not_v1}

        self.assertEqual(
            set(missing_v1),
            # This was an incorrectly classified batch due to our dex_swaps estimation
            # The V1 query estimates dex_swaps = 1 (while there were none).
            # We could probably adapt the query to
            {"0x595ab6fb4b6723473b0c77009aa39df4939f32510ad3a5c3f81ae69eec6fdea1"},
        )
        self.assertEqual(set(missing_v2), set())

        for tx_hash in data.overlap:
            x = data.v1[tx_hash]
            y = data.v2[tx_hash]
            prepped_items = {"V1": x, "V2": y}
            self.assertEqual(
                len(x),
                len(y),
                f"Failed {table_name} at {tx_hash} on\n {json.dumps(prepped_items)}",
            )

    def test_final_token_balance_sheet(self):
        table_name = "final_token_balance_sheet"
        data = self.get_cte_results(
            table_name,
            v1_cache="01GJR2PTEXWT63HVG6WZ7PXB4R",
            v2_cache="01GJR2Q0CWVKKRZ7J53RC463X9",
        )
        print(str(data))
        # Probably need to investigate this difference a bit more.
        # v1_not_v2 = 172 batches
        # v2_not_v1 = 107 batches
        # overlap = 3062 batches

    def test_similar_slippage_for_period(self):
        table_name = "results"
        v1_result, v2_result = self.get_cte_rows(
            table_name,
            v1_cache="01GJR7DV87RM5D5W2T25FTXA0F",
            v2_cache="01GJR7G2JKADDZDY94BP96V1C6",
        )
        v1_slippage = SplitSlippages.from_data_set(v1_result)
        v2_slippage = SplitSlippages.from_data_set(v2_result)

        delta = 1  # decimal places ETH.
        self.assertLess(
            v1_slippage.sum_negative() / 10**18,  # 1.9123 ETH
            v2_slippage.sum_negative() / 10**18,  # 1.9029 ETH
            1,  # |v1 - v2| ~ 0.0094 --> 9.4 USD (with ETH at 1000)
        )

        self.assertAlmostEqual(
            v1_slippage.sum_positive() / 10**18,  # 2.625 ETH
            v2_slippage.sum_positive() / 10**18,  # 2.629 ETH
            2,  # |v1 - v2| ~ 0.004 --> 4 USD (with ETH at 1000)
        )

        # an even strong assertion because I consider the above a bug on negative slippage is
        self.assertLess(
            abs(v1_slippage.sum_negative() - v2_slippage.sum_negative()) / 10**18,
            0.01,
        )
        # which says difference is less than 0.01 ETH
        # The above fails when decimals = 2 (probably because of rounding)
        # and decimals = 1 only asserts that the difference is < 0.1 ETH


if __name__ == "__main__":
    unittest.main()
