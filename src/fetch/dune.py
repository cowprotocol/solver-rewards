"""All Dune related query fetching is defined here in the DuneFetcherClass"""

from typing import Optional

from dune_client.client import DuneClient
from dune_client.query import QueryBase
from dune_client.types import QueryParameter, DuneRecord

from src.logger import set_log, log_saver
from src.models.accounting_period import AccountingPeriod
from src.queries import QUERIES, QueryData
from src.utils.print_store import Category

log = set_log(__name__)


class DuneFetcher:
    """
    Class Contains DuneAPI Instance and Accounting Period along with several get methods
    for various Dune Queries.
    """

    dune: DuneClient
    period: AccountingPeriod
    blockchain: str

    def __init__(
        self,
        dune: DuneClient,
        blockchain: str,
        period: AccountingPeriod,
    ):
        self.dune = dune
        self.blockchain = blockchain
        self.period = period
        # Already have period set, so we might as well store this upon construction.
        # This may become an issue when we make the fetchers async;
        # since python does not allow async constructors
        self.start_block, self.end_block = self.get_block_interval()

    def _period_params(self) -> list[QueryParameter]:
        """Easier access to these parameters."""
        return self.period.as_query_params()

    def _network_and_period_params(self) -> list[QueryParameter]:
        """Easier access to parameters for network and accounting period."""
        network_param = QueryParameter.text_type("blockchain", self.blockchain)
        period_params = self._period_params()

        return period_params + [network_param]

    @staticmethod
    def _parameterized_query(
        query_data: QueryData, params: list[QueryParameter]
    ) -> QueryBase:
        return query_data.with_params(params)

    def _get_query_results(
        self, query: QueryBase, job_id: Optional[str] = None
    ) -> list[dict[str, str]]:
        """Internally every dune query execution is routed through here."""
        log.info(f"Fetching {query.name} from query: {query}")
        if not job_id:
            exec_result = self.dune.refresh(query, ping_frequency=15)
        else:
            exec_result = self.dune.get_result(job_id)

        log.info(f"Fetch completed for execution {exec_result.execution_id}")
        log_saver.print(
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
                QUERIES["PERIOD_BLOCK_INTERVAL"], self._network_and_period_params()
            )
        )
        assert len(results) == 1, "Block Interval Query should return only 1 result!"
        return str(results[0]["start_block"]), str(results[0]["end_block"])

    def get_vouches(self) -> list[DuneRecord]:
        """
        Fetches & Returns Parsed Results for VouchRegistry query.
        """
        return self._get_query_results(
            query=self._parameterized_query(
                query_data=QUERIES["VOUCH_REGISTRY"],
                params=[
                    QueryParameter.date_type("end_time", self.period.end),
                    QueryParameter.enum_type("vouch_cte_name", "named_results"),
                    QueryParameter.text_type("blockchain", self.blockchain),
                ],
            )
        )

    def get_period_slippage(self, job_id: Optional[str] = None) -> list[DuneRecord]:
        """
        Executes & Fetches results of slippage query per solver for specified accounting period.
        Returns a class representation of the results as two lists (positive & negative).
        """
        params = self._network_and_period_params()
        # trigger dashboard update
        self.dune.execute(
            self._parameterized_query(QUERIES["DASHBOARD_SLIPPAGE"], params=params)
        )

        return self._get_query_results(
            self._parameterized_query(QUERIES["PERIOD_SLIPPAGE"], params=params),
            job_id,
        )

    def get_service_fee_status(self) -> list[DuneRecord]:
        """
        Fetches & Returns Parsed Results for VouchRegistry query.
        """
        return self._get_query_results(
            query=self._parameterized_query(
                query_data=QUERIES["SERVICE_FEE_STATUS"],
                params=self._network_and_period_params(),
            )
        )
