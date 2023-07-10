"""All Dune related query fetching is defined here in the DuneFetcherClass"""
from typing import Optional

from dune_client.client import DuneClient
from dune_client.query import Query
from dune_client.types import QueryParameter, DuneRecord

from src.constants import RECOGNIZED_BONDING_POOLS
from src.fetch.token_list import get_trusted_tokens
from src.logger import set_log
from src.models.accounting_period import AccountingPeriod
from src.queries import QUERIES, QueryData
from src.utils.print_store import PrintStore, Category

log = set_log(__name__)


class DuneFetcher:
    """
    Class Contains DuneAPI Instance and Accounting Period along with several get methods
    for various Dune Queries.
    """

    dune: DuneClient
    period: AccountingPeriod
    log_saver: PrintStore

    def __init__(
        self,
        dune: DuneClient,
        period: AccountingPeriod,
    ):
        self.dune = dune
        self.period = period
        self.log_saver = PrintStore()
        # Already have period set, so we might as well store this upon construction.
        # This may become an issue when we make the fetchers async;
        # since python does not allow async constructors
        self.start_block, self.end_block = self.get_block_interval()

    def _period_params(self) -> list[QueryParameter]:
        """Easier access to these parameters."""
        return self.period.as_query_params()

    @staticmethod
    def _parameterized_query(
        query_data: QueryData, params: list[QueryParameter]
    ) -> Query:
        return query_data.with_params(params)

    def _get_query_results(
        self, query: Query, job_id: Optional[str] = None
    ) -> list[dict[str, str]]:
        """Internally every dune query execution is routed through here."""
        log.info(f"Fetching {query.name} from query: {query}")
        if not job_id:
            exec_result = self.dune.refresh(query, ping_frequency=15)
        else:
            exec_result = self.dune.get_result(job_id)

        log.info(f"Fetch completed for execution {exec_result.execution_id}")
        self.log_saver.print(
            f"{query.name} execution ID: {exec_result.execution_id}", Category.EXECUTION
        )
        # TODO - use a real logger:
        #  https://github.com/cowprotocol/dune-client/issues/34
        if exec_result.result is not None:
            log.debug(f"Execution result metadata {exec_result.result.metadata}")
        else:
            log.warning(f"No execution results found for {exec_result.execution_id}")
        return exec_result.get_rows()

    def get_block_interval(self) -> tuple[str, str]:
        """Returns block numbers corresponding to date interval"""
        results = self._get_query_results(
            self._parameterized_query(
                QUERIES["PERIOD_BLOCK_INTERVAL"], self._period_params()
            )
        )
        assert len(results) == 1, "Block Interval Query should return only 1 result!"
        return str(results[0]["start_block"]), str(results[0]["end_block"])

    def get_vouches(self) -> list[DuneRecord]:
        """
        Fetches & Returns Parsed Results for VouchRegistry query.
        """
        pool_values = ",\n".join(RECOGNIZED_BONDING_POOLS)
        return self._get_query_results(
            query=self._parameterized_query(
                query_data=QUERIES["VOUCH_REGISTRY"],
                params=[
                    QueryParameter.date_type("EndTime", self.period.end),
                    QueryParameter.text_type("BondingPoolData", pool_values),
                    QueryParameter.enum_type("VOUCH_CTE_NAME", "valid_vouches"),
                ],
            )
        )

    def get_period_slippage(self, job_id: Optional[str] = None) -> list[DuneRecord]:
        """
        Executes & Fetches results of slippage query per solver for specified accounting period.
        Returns a class representation of the results as two lists (positive & negative).
        """
        token_list = get_trusted_tokens()
        params = self._period_params() + [
            QueryParameter.text_type("TxHash", "0x"),
            QueryParameter.text_type("TokenList", ",".join(token_list)),
        ]
        # trigger dashboard update
        self.dune.execute(
            self._parameterized_query(QUERIES["DASHBOARD_SLIPPAGE"], params=params)
        )

        return self._get_query_results(
            self._parameterized_query(
                QUERIES["PERIOD_SLIPPAGE"],
                params=self._period_params()
                + [
                    QueryParameter.text_type("TxHash", "0x"),
                    QueryParameter.text_type("TokenList", ",".join(token_list)),
                ],
            ),
            job_id,
        )
