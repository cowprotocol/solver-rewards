"""All Dune related query fetching is defined here in the DuneFetcherClass"""
from typing import Optional

import pandas as pd
from dune_client.client import DuneClient
from dune_client.query import Query
from dune_client.types import QueryParameter, DuneRecord

from src.fetch.cow_rewards import aggregate_orderbook_rewards
from src.fetch.token_list import get_trusted_tokens
from src.logger import set_log
from src.models.accounting_period import AccountingPeriod
from src.models.period_totals import PeriodTotals
from src.models.slippage import SplitSlippages
from src.models.split_transfers import SplitTransfers
from src.models.transfer import Transfer
from src.models.vouch import RECOGNIZED_BONDING_POOLS, parse_vouches
from src.pg_client import DualEnvDataframe
from src.queries import QUERIES, DuneVersion, QueryData
from src.utils.print_store import PrintStore

log = set_log(__name__)

# TODO - eliminate the use of Address class (or refactor)
#  because Web3.toChecksumAddress is very SLOW and should be replaced by str.lower()
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
        dune_version: DuneVersion = DuneVersion.V2,
    ):
        self.dune = dune
        self.period = period
        self.log_saver = PrintStore()
        self.dune_version = dune_version
        # Already have period set, so we might as well store this upon construction.
        # This may become an issue when we make the fetchers async;
        # since python does not allow async constructors
        self.start_block, self.end_block = self.get_block_interval()

    def _period_params(self) -> list[QueryParameter]:
        """Easier access to these parameters."""
        return self.period.as_query_params()

    def _parameterized_query(
        self, query_data: QueryData, params: list[QueryParameter]
    ) -> Query:
        return query_data.with_params(params, dune_version=self.dune_version)

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

    def get_eth_spent(self) -> list[Transfer]:
        """
        Fetches ETH spent on successful settlements by all solvers during `period`
        """
        results = self._get_query_results(
            self._parameterized_query(QUERIES["ETH_SPENT"], self._period_params())
        )
        return [Transfer.from_dict(t) for t in results]

    def get_risk_free_batches(self) -> set[str]:
        """Fetches Risk Free Batches from Dune"""
        results = self._get_query_results(
            self._parameterized_query(
                QUERIES["RISK_FREE_BATCHES"], self._period_params()
            )
        )
        return {row["tx_hash"].lower() for row in results}

    def get_trade_counts(self) -> list[DuneRecord]:
        """Fetches Trade Counts for Period"""
        return self._get_query_results(
            query=self._parameterized_query(
                query_data=QUERIES["TRADE_COUNT"],
                params=[
                    QueryParameter.text_type("start_block", self.start_block),
                    QueryParameter.text_type("end_block", self.end_block),
                ],
            )
        )

    def get_cow_rewards(self) -> list[Transfer]:
        """
        Fetches COW token rewards from orderbook database returning a list of Transfers
        """
        print(
            f"Fetching CoW Rewards for block interval {self.start_block}, {self.end_block}"
        )
        per_order_df = DualEnvDataframe.get_orderbook_rewards(
            self.start_block, self.end_block
        )
        cow_rewards_df = aggregate_orderbook_rewards(
            per_order_df,
            risk_free_transactions=self.get_risk_free_batches(),
        )

        # Validation of results - using characteristics of results from two sources.
        trade_counts = self.get_trade_counts()
        # Number of trades per solver retrieved from orderbook agrees ethereum events.
        duplicates = pd.concat(
            [
                pd.DataFrame(trade_counts),
                cow_rewards_df[["receiver", "num_trades"]].rename(
                    columns={"receiver": "solver"}
                ),
            ]
        ).drop_duplicates(keep=False)

        assert len(duplicates) == 0, f"solver sets disagree: {duplicates}"
        return Transfer.from_dataframe(cow_rewards_df)

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

    def get_period_totals(self) -> PeriodTotals:
        """
        Fetches & Returns Dune Results for accounting period totals.
        """
        data_set = self._get_query_results(
            query=self._parameterized_query(
                query_data=QUERIES["PERIOD_TOTALS"], params=self._period_params()
            )
        )
        assert len(data_set) == 1
        rec = data_set[0]
        return PeriodTotals(
            period=self.period,
            execution_cost_eth=int(rec["execution_cost_eth"]),
            cow_rewards=int(rec["cow_rewards"]),
            realized_fees_eth=int(rec["realized_fees_eth"]),
        )

    def get_mev_kickback(self) -> list[DuneRecord]:
        """Executes & Fetches results of Solver MEV Kickback for period"""
        return self._get_query_results(
            self._parameterized_query(
                QUERIES["PERIOD_MEV_KICKBACK"], params=self._period_params()
            ),
        )

    def get_period_slippage(self, job_id: Optional[str] = None) -> list[DuneRecord]:
        """
        Executes & Fetches results of slippage query per solver for specified accounting period.
        Returns a class representation of the results as two lists (positive & negative).
        """
        token_list = get_trusted_tokens()
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

    def get_transfers(self) -> list[Transfer]:
        """Fetches and returns slippage-adjusted Transfers for solver reimbursement"""
        # TODO - fetch these three results asynchronously!
        reimbursements = self.get_eth_spent()
        rewards = self.get_cow_rewards()
        split_transfers = SplitTransfers(
            period=self.period,
            mixed_transfers=reimbursements + rewards,
            log_saver=self.log_saver,
        )
        return split_transfers.process(
            slippages=SplitSlippages.from_data_set(self.get_period_slippage()),
            cow_redirects=parse_vouches(self.get_vouches()),
        )
