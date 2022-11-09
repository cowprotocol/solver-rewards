"""All Dune related query fetching is defined here in the DuneFetcherClass"""
import pandas as pd
from dune_client.client import DuneClient
from dune_client.types import QueryParameter, Address
from duneapi.api import DuneAPI
from duneapi.types import DuneQuery, QueryParameter as LegacyParameter, Network

from src.fetch.cow_rewards import aggregate_orderbook_rewards
from src.fetch.token_list import get_trusted_tokens
from src.models.accounting_period import AccountingPeriod
from src.models.period_totals import PeriodTotals
from src.models.slippage import SplitSlippages, slippage_query
from src.models.split_transfers import SplitTransfers
from src.models.transfer import Transfer
from src.models.vouch import Vouch, RECOGNIZED_BONDING_POOLS, parse_vouches
from src.pg_client import DualEnvDataframe
from src.query_tracker import QUERIES
from src.utils.dataset import index_by
from src.utils.print_store import PrintStore
from src.utils.query_file import open_query


class DuneFetcher:
    """
    Class Contains DuneAPI Instance and Accounting Period along with several get methods
    for various Dune Queries.
    """

    dune_v1: DuneAPI
    dune: DuneClient
    period: AccountingPeriod
    log_saver: PrintStore

    def __init__(self, dune_v1: DuneAPI, dune: DuneClient, period: AccountingPeriod):
        self.dune_v1 = dune_v1
        self.dune = dune
        self.period = period
        self.log_saver = PrintStore()

    def get_block_interval(self) -> tuple[str, str]:
        """Returns block numbers corresponding to date interval"""
        query = QUERIES["PERIOD_BLOCK_INTERVAL"].with_params(
            self.period.as_query_params()
        )
        query.name = f"Block Interval for Accounting Period {self}"
        results = self.dune.refresh(query).get_rows()
        assert len(results) == 1, "Block Interval Query should return only 1 result!"
        return str(results[0]["start_block"]), str(results[0]["end_block"])

    def get_eth_spent(self) -> list[Transfer]:
        """
        Fetches ETH spent on successful settlements by all solvers during `period`
        """
        query = QUERIES["ETH_SPENT"].with_params(self.period.as_query_params())
        print(query)
        return [Transfer.from_dict(t) for t in self.dune.refresh(query).get_rows()]

    def get_risk_free_batches(self) -> set[str]:
        """Fetches Risk Free Batches from Dune"""
        results = self.dune.refresh(
            QUERIES["RISK_FREE_BATCHES"].with_params(self.period.as_query_params())
        ).get_rows()
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
        query = QUERIES["TRADE_COUNT"].with_params(
            [
                QueryParameter.text_type("start_block", start_block),
                QueryParameter.text_type("end_block", end_block),
            ]
        )
        dune_trade_counts = self.dune.refresh(query).get_rows()
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
                    open_query("vouch_registry.sql"),
                    "select * from valid_vouches",
                ]
            ),
            network=Network.MAINNET,
            name="Solver Reward Targets",
            parameters=[
                LegacyParameter.date_type("EndTime", self.period.end),
                LegacyParameter.text_type("BondingPoolData", pool_values),
            ],
        )
        return parse_vouches(self.dune_v1.fetch(query))

    def get_period_totals(self) -> PeriodTotals:
        """
        Fetches & Returns Dune Results for accounting period totals.
        """
        query = QUERIES["PERIOD_TOTALS"].with_params(self.period.as_query_params())
        data_set = self.dune.refresh(query).get_rows()
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
                LegacyParameter.date_type("StartTime", self.period.start),
                LegacyParameter.date_type("EndTime", self.period.end),
                LegacyParameter.text_type("TxHash", "0x"),
                LegacyParameter.text_type("TokenList", ",".join(token_list)),
            ],
        )
        data_set = self.dune_v1.fetch(query)
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
