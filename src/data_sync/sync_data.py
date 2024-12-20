"""Main Entry point for running any sync job"""

import argparse
import asyncio
import os
from dataclasses import dataclass
from dotenv import load_dotenv
from web3 import Web3
from src.fetch.orderbook import OrderbookFetcher, OrderbookEnv
from src.config import AccountingConfig, Network, web3
from src.logger import set_log
from src.models.tables import SyncTable
from src.data_sync.common import compute_block_and_month_range
from src.models.block_range import BlockRange


log = set_log(__name__)


@dataclass
class ScriptArgs:
    """Runtime arguments' parser/initializer"""

    sync_table: SyncTable

    def __init__(self) -> None:
        parser = argparse.ArgumentParser("Dune Community Sources Sync")
        parser.add_argument(
            "--sync-table",
            type=SyncTable,
            required=True,
            choices=list(SyncTable),
        )
        arguments, _ = parser.parse_known_args()
        self.sync_table: SyncTable = arguments.sync_table


async def sync_data_to_db(  # pylint: disable=too-many-arguments
    type_of_data: str,
    node: Web3,
    orderbook: OrderbookFetcher,
    network: str,
    config: AccountingConfig,
    recompute_previous_month: bool,
) -> None:
    """
    Order/Batch data Sync Logic. The recompute_previous_month flag, when enabled,
    forces a recomputation of the previous month. If it is set to False, previous month
    is still recomputed when the current date is the first day of the current month.
    """

    block_range_list, months_list = compute_block_and_month_range(
        node, recompute_previous_month
    )
    # we note that the block range computed above is meant to be interpreted as
    # a closed interval
    for i, (start_block, end_block) in enumerate(block_range_list):
        network_name = "ethereum" if network == "mainnet" else network
        table_name = type_of_data + "_data_" + network_name + "_" + months_list[i]
        block_range = BlockRange(block_from=start_block, block_to=end_block)
        log.info(
            f"About to process block range ({start_block}, {end_block}) for month {months_list[i]}"
        )
        if type_of_data == "batch":
            data = orderbook.get_batch_data(block_range, config)
        else:
            data = orderbook.get_order_data(block_range, config)
        log.info("SQL query successfully executed. About to update analytics table.")

        data.to_sql(
            table_name,
            OrderbookFetcher.pg_engine(OrderbookEnv.ANALYTICS),
            if_exists="replace",
            index=False,
        )
        log.info(
            f"{type_of_data} data sync run completed successfully for month {months_list[i]}"
        )


def sync_data() -> None:
    """
    Main function
    """
    load_dotenv()
    args = ScriptArgs()
    orderbook = OrderbookFetcher()
    network = os.environ.get("NETWORK", "mainnet")
    config = AccountingConfig.from_network(Network(os.environ["NETWORK"]))
    log.info(f"Network is set to: {network}")

    if args.sync_table == SyncTable.BATCH_DATA:
        asyncio.run(
            sync_data_to_db(
                "batch",
                web3,
                orderbook,
                network,
                config,
                recompute_previous_month=False,
            )
        )
    elif args.sync_table == SyncTable.ORDER_DATA:
        asyncio.run(
            sync_data_to_db(
                "order",
                web3,
                orderbook,
                network,
                config,
                recompute_previous_month=False,
            )
        )
    else:
        log.error(f"unsupported sync_table '{args.sync_table}'")


if __name__ == "__main__":
    sync_data()
