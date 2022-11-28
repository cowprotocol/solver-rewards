from typing import Optional

from dune_client.client import DuneClient
from dune_client.query import Query


def exec_or_get(dune: DuneClient, query: Query, result_id: Optional[str] = None):
    if not result_id:
        results = dune.refresh(query)
        print(f"Execution ID: {results.execution_id}")
        return results
    return dune.get_result(result_id)
