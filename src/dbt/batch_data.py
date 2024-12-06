"""Main Entry point for batch data sync"""

import os
from dotenv import load_dotenv
from web3 import Web3
from src.fetch.orderbook import OrderbookFetcher, OrderbookEnv
from src.logger import set_log
from src.dbt.common import compute_block_and_month_range
from src.models.block_range import BlockRange


log = set_log(__name__)


async def sync_batch_data(
    node: Web3,
    orderbook: OrderbookFetcher,
    network: str,
    recompute_previous_month: bool,
) -> None:
    """
    Batch data Sync Logic. The recompute_previous_month flag, when enabled, forces a recomputation
    of the previous month. If it is set to False, previous month is still recomputed when the current
    date is the first day of the current month.
    """

    block_range_list, months_list, is_even = compute_block_and_month_range(
        node, recompute_previous_month
    )
    for i, _ in enumerate(block_range_list):
        start_block = block_range_list[i][0]
        end_block = block_range_list[i][1]
        if is_even[i]:
            table_name = "raw_batch_data_latest_even_month_" + network.lower()
        else:
            table_name = "raw_batch_data_latest_odd_month_" + network.lower()
        block_range = BlockRange(block_from=start_block, block_to=end_block)
        log.info(
            f"About to process block range ({start_block}, {end_block}) for month {months_list[i]}"
        )
        batch_data = orderbook.get_batch_data(block_range)
        log.info("SQL query successfully executed. About to update analytics table.")
        batch_data.to_sql(
            table_name,
            orderbook._pg_engine(OrderbookEnv.ANALYTICS),
            if_exists="replace",
        )
        log.info(
            f"batch data sync run completed successfully for month {months_list[i]}"
        )
