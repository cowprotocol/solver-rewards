"""All Dune related query fetching is defined here in the DuneFetcherClass"""
import pandas as pd
from duneapi.api import DuneAPI
from duneapi.types import DuneQuery, QueryParameter, Network, Address
from duneapi.util import open_query

from src.fetch.cow_rewards import aggregate_orderbook_rewards
from src.fetch.token_list import get_trusted_tokens
from src.models.accounting_period import AccountingPeriod
from src.models.period_totals import PeriodTotals
from src.models.slippage import SplitSlippages, slippage_query
from src.models.split_transfers import SplitTransfers
from src.models.transfer import Transfer
from src.models.vouch import Vouch, RECOGNIZED_BONDING_POOLS, parse_vouches
from src.pg_client import DualEnvDataframe
from src.utils.dataset import index_by
from src.utils.print_store import PrintStore
from src.utils.query_file import query_file, dashboard_file


class DuneFetcher:
    """
    Class Contains DuneAPI Instance and Accounting Period along with several get methods
    for various Dune Queries.
    """

    dune: DuneAPI
    period: AccountingPeriod
    log_saver: PrintStore

    def __init__(self, dune: DuneAPI, period: AccountingPeriod):
        self.dune = dune
        self.period = period
        self.log_saver = PrintStore()

    def get_block_interval(self) -> tuple[str, str]:
        """Returns block numbers corresponding to date interval"""
        results = self.dune.fetch(
            query=DuneQuery.from_environment(
                raw_sql=open_query(query_file("period_block_interval.sql")),
                name=f"Block Interval for Accounting Period {self.period}",
                network=Network.MAINNET,
                parameters=[
                    # TODO - There are too many occurrences of this pair.
                    #  Make AccountingPeriod.as_query_params
                    QueryParameter.date_type("StartTime", self.period.start),
                    QueryParameter.date_type("EndTime", self.period.end),
                ],
            )
        )
        assert len(results) == 1, "Block Interval Query should return only 1 result!"
        return str(results[0]["start_block"]), str(results[0]["end_block"])

    def get_eth_spent(self) -> list[Transfer]:
        """
        Fetches ETH spent on successful settlements by all solvers during `period`
        """
        query = DuneQuery.from_environment(
            raw_sql=open_query(query_file("eth_spent.sql")),
            network=Network.MAINNET,
            name="ETH Reimbursement",
            parameters=[
                QueryParameter.date_type("StartTime", self.period.start),
                QueryParameter.date_type("EndTime", self.period.end),
            ],
        )
        return [Transfer.from_dict(t) for t in self.dune.fetch(query)]

    def get_risk_free_batches(self) -> set[str]:
        """Fetches Risk Free Batches from Dune"""
        results = self.dune.fetch(
            query=DuneQuery.from_environment(
                raw_sql=open_query(query_file("risk_free_batches.sql")),
                network=Network.MAINNET,
                name="Risk Free Batches",
                parameters=[
                    QueryParameter.date_type("StartTime", self.period.start),
                    QueryParameter.date_type("EndTime", self.period.end),
                ],
            )
        )
        return {row["tx_hash"].lower() for row in results}

    def get_cow_rewards(self) -> list[Transfer]:
        """
        Fetches COW token rewards from orderbook database returning a list of Transfers
        """
        start_block, end_block = self.get_block_interval()
        print(f"Fetching CoW Rewards for block interval {start_block}, {end_block}")
        per_order_df = DualEnvDataframe.get_orderbook_rewards(start_block, end_block)
        cow_rewards_df = aggregate_orderbook_rewards(
            per_order_df,
            risk_free_transactions=self.get_risk_free_batches(),
        )

        # Validation of results - using characteristics of results from two sources.
        dune_trade_counts = self.dune.fetch(
            query=DuneQuery.from_environment(
                raw_sql=open_query(query_file("dune_trade_counts.sql")),
                network=Network.MAINNET,
                name="Trade Counts",
                parameters=[
                    QueryParameter.text_type("start_block", start_block),
                    QueryParameter.text_type("end_block", end_block),
                ],
            )
        )
        # Number of trades per solver retrieved from orderbook agrees ethereum events.
        duplicates = pd.concat(
            [
                pd.DataFrame(dune_trade_counts),
                cow_rewards_df[["receiver", "num_trades"]].rename(
                    columns={"receiver": "solver"}
                ),
            ]
        ).drop_duplicates(keep=False)

        assert len(duplicates) == 0, f"solver sets disagree: {duplicates}"
        return Transfer.from_dataframe(cow_rewards_df)

    def get_vouches(self) -> dict[Address, Vouch]:
        """
        Fetches & Returns Parsed Results for VouchRegistry query.
        """

        pool_values = ",\n           ".join(RECOGNIZED_BONDING_POOLS)
        query = DuneQuery.from_environment(
            raw_sql="\n".join(
                [
                    open_query(query_file("vouch_registry.sql")),
                    "select * from valid_vouches",
                ]
            ),
            network=Network.MAINNET,
            name="Solver Reward Targets",
            parameters=[
                QueryParameter.date_type("EndTime", self.period.end),
                QueryParameter.text_type("BondingPoolData", pool_values),
            ],
        )
        return parse_vouches(self.dune.fetch(query))

    def get_period_totals(self) -> PeriodTotals:
        """
        Fetches & Returns Dune Results for accounting period totals.
        """
        query = DuneQuery.from_environment(
            raw_sql=open_query(dashboard_file("period-totals.sql")),
            network=Network.MAINNET,
            name="Accounting Period Totals",
            parameters=[
                QueryParameter.date_type("StartTime", self.period.start),
                QueryParameter.date_type("EndTime", self.period.end),
            ],
        )
        data_set = self.dune.fetch(query)
        assert len(data_set) == 1
        rec = data_set[0]
        return PeriodTotals(
            period=self.period,
            execution_cost_eth=int(rec["execution_cost_eth"]),
            cow_rewards=int(rec["cow_rewards"]),
            realized_fees_eth=int(rec["realized_fees_eth"]),
        )

    def get_period_slippage(self) -> SplitSlippages:
        """
        Executes & Fetches results of slippage query per solver for specified accounting period.
        Returns a class representation of the results as two lists (positive & negative).
        """
        token_list = get_trusted_tokens()
        query = DuneQuery.from_environment(
            raw_sql=slippage_query(),
            network=Network.MAINNET,
            name="Slippage Accounting",
            parameters=[
                QueryParameter.date_type("StartTime", self.period.start),
                QueryParameter.date_type("EndTime", self.period.end),
                QueryParameter.text_type("TxHash", "0x"),
                QueryParameter.text_type("TokenList", ",".join(token_list)),
            ],
        )
        data_set = self.dune.fetch(query)
        return SplitSlippages.from_data_set(data_set)

    def get_transfers(self) -> list[Transfer]:
        """Fetches and returns slippage-adjusted Transfers for solver reimbursement"""
        reimbursements = self.get_eth_spent()
        rewards = self.get_cow_rewards()
        split_transfers = SplitTransfers(self.period, reimbursements + rewards)
        negative_slippage = self.get_period_slippage().negative

        return split_transfers.process(
            indexed_slippage=index_by(negative_slippage, "solver_address"),
            cow_redirects=self.get_vouches(),
            log_saver=self.log_saver,
        )
