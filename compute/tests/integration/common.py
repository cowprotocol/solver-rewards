from typing import Optional

from dune_client.client import DuneClient
from dune_client.query import Query
from dune_client.types import QueryParameter

from compute.src.models.accounting_period import AccountingPeriod
from compute.src.queries import QUERIES


def exec_or_get(dune: DuneClient, query: Query, result_id: Optional[str] = None):
    if not result_id:
        results = dune.refresh(query)
        print(f"Execution ID: {results.execution_id}")
        return results
    return dune.get_result(result_id)


def get_slippage_cte_rows(
    dune: DuneClient,
    cte_name: str,
    period: AccountingPeriod,
    tx_hash: Optional[str] = None,
    v1_cache: Optional[str] = None,
    v2_cache: Optional[str] = None,
):
    slippage_query = QUERIES["PERIOD_SLIPPAGE"]
    v1_query_id = slippage_query.v1_query.query_id
    v2_query_id = slippage_query.v2_query.query_id

    parameters = period.as_query_params()
    parameters.append(QueryParameter.enum_type("CTE_NAME", cte_name))
    if tx_hash:
        parameters.append(QueryParameter.text_type("TxHash", tx_hash))

    v1_results = exec_or_get(
        dune,
        Query(v1_query_id, params=parameters),
        v1_cache,
    )
    v2_results = exec_or_get(
        dune,
        Query(v2_query_id, params=parameters),
        v2_cache,
    )

    v1_rows = v1_results.get_rows()
    v2_rows = v2_results.get_rows()
    return v1_rows, v2_rows
