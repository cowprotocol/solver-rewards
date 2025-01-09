"""Main Entry point for running any sync job"""

import argparse
import asyncio
import datetime
import os
from dataclasses import dataclass

from dateutil.relativedelta import (
    relativedelta,
)  # dateutil is currently not explicitly required in requirement.in, only installed via dune
from dotenv import load_dotenv
from web3 import Web3

from src.fetch.orderbook import OrderbookFetcher
from src.config import AccountingConfig, Network, web3
from src.logger import set_log
from src.models.tables import SyncTable
from src.data_sync.common import (
    compute_block_range,
    compute_time_range,
)


log = set_log(__name__)


@dataclass
class ScriptArgs:
    """Runtime arguments' parser/initializer"""

    sync_table: SyncTable
    start_time: datetime.datetime
    end_time: datetime.datetime

    def __init__(self) -> None:
        parser = argparse.ArgumentParser("Dune Community Sources Sync")
        parser.add_argument(
            "--sync-table",
            type=SyncTable,
            required=True,
            choices=list(SyncTable),
        )
        parser.add_argument(
            "--start-time",
            type=datetime.datetime.fromisoformat,
            default=None,
            help=(
                "Start of the time range for syncing (inclusive). If not set, it defaults to the "
                "beginning of the current month."
            ),
        )
        parser.add_argument(
            "--end-time",
            type=datetime.datetime.fromisoformat,
            default=None,
            help=(
                "End of the time range for syncing (inclusive). If not set, it defaults to the "
                "beginning of the next month."
            ),
        )
        arguments, _ = parser.parse_known_args()
        self.sync_table: SyncTable = arguments.sync_table

        # parse time arguments
        current_time = datetime.datetime.now(datetime.timezone.utc)
        if arguments.start_time is None:
            # default start time is the first of the month
            self.start_time = datetime.datetime(
                current_time.year, current_time.month, 1
            )
            log.info(f"No start time set, using beginning of month {self.start_time}.")
        else:
            self.start_time = arguments.start_time
        if arguments.end_time is None:
            # default end time (exclusive) is the start of the next month
            self.end_time = datetime.datetime(
                current_time.year, current_time.month, 1
            ) + relativedelta(months=1)
            log.info(
                f"No start time set, using beginning of next month {self.end_time}."
            )
        else:
            self.end_time: datetime.datetime = arguments.end_time
        self.start_time = self.start_time.replace(tzinfo=datetime.timezone.utc)
        self.end_time = self.end_time.replace(tzinfo=datetime.timezone.utc)


async def sync_data_to_db(  # pylint: disable=too-many-arguments
    type_of_data: str,
    node: Web3,
    orderbook: OrderbookFetcher,
    config: AccountingConfig,
    start_time: datetime.datetime,
    end_time: datetime.datetime,
) -> None:
    """Order and Batch data Sync Logic."""
    time_range_list = compute_time_range(start_time, end_time)
    for start_time_month, end_time_month in time_range_list:
        month = start_time_month.strftime("%Y_%m")
        network_name = config.dune_config.dune_blockchain
        table_name = type_of_data + "_data_" + network_name + "_" + month
        block_range = compute_block_range(start_time_month, end_time_month, node)
        log.info(f"About to process {block_range}) for month {month}")
        if type_of_data == "batch":
            data = orderbook.get_batch_data(block_range, config)
        else:
            data = orderbook.get_order_data(block_range, config)
        log.info("SQL query successfully executed. About to update analytics table.")

        orderbook.write_data(type_of_data, data, table_name)

        log.info(
            f"{type_of_data} data sync run completed successfully for month {month}."
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

    match args.sync_table:
        case SyncTable.BATCH_DATA:
            type_of_data = "batch"
        case SyncTable.ORDER_DATA:
            type_of_data = "order"
        case _:
            raise ValueError(f"unsupported sync_table '{args.sync_table}'")

    asyncio.run(
        sync_data_to_db(
            type_of_data,  # just pass the sync table directly
            web3,
            orderbook,
            config,
            args.start_time,
            args.end_time,
        )
    )


if __name__ == "__main__":
    sync_data()
