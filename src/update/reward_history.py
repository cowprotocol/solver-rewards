"""
This module fetches the orderbook rewards from the prod and barn orderbook databases
and injects them into Dune as a user generated view. Note that the table is very large,
so results are paginated across tables of the form

dune_user_generated.cow_order_rewards_{{Environment}}_page_{{Page}}

a complete table is also built as the union of these under the name

dune_user_generated.cow_order_rewards_{{Environment}}

The intention is to run this script once every 24 hours.
We can optimize this data transfer by evaluating the checksum.
Essentially, it should only have to update the last page (or append a new page)
as long as the previous pages have not been tampered with.
"""
from __future__ import annotations

import logging
import os
from dataclasses import dataclass
from typing import Optional

from duneapi.api import DuneAPI
from duneapi.types import DuneQuery, Network
from duneapi.util import open_query
from pandas import DataFrame

from src.constants import QUERY_PATH
from src.pg_client import pg_hex2bytea, DualEnvDataframe
from src.update.utils import Environment, multi_push_view, update_args

log = logging.getLogger(__name__)
log.level = logging.INFO

ORDER_REWARDS_QUERY = int(os.environ.get("ORDER_REWARDS_QUERY", 1476356))


@dataclass
class OrderRewards:
    """OrderReward values"""

    solver: str
    tx_hash: str
    order_uid: str
    amount: float
    safe_liquidity: Optional[bool]

    @classmethod
    def from_dataframe(cls, pdf: DataFrame) -> list[OrderRewards]:
        """Constructs OrderReward records from Dataframe"""
        return [
            cls(
                solver=row["solver"],
                tx_hash=row["tx_hash"],
                order_uid=row["order_uid"],
                amount=float(row["amount"]),
                safe_liquidity=row["safe_liquidity"],
            )
            for _, row in pdf.iterrows()
        ]

    def __str__(self) -> str:
        solver, tx_hash, order_id = list(
            map(pg_hex2bytea, [self.solver, self.tx_hash, self.order_uid])
        )
        safe = self.safe_liquidity if self.safe_liquidity is not None else "Null"
        return f"('{order_id}','{solver}','{tx_hash}',{self.amount},{safe})"


def fetch_and_push_order_rewards(
    dune: DuneAPI, env: Environment, drop_first: bool = False
) -> None:
    """Fetches and parses Order Rewards from Orderbook, pushes them to Dune."""
    if drop_first:
        drop_all_pages(dune, env)
    log.info("Fetching and Merging Orderbook Rewards")
    rewards = OrderRewards.from_dataframe(
        DualEnvDataframe.get_orderbook_rewards(
            start_block="15771267",
            end_block="999999999",  # 320 years from now with 12-second block times
        )
    )
    # TODO - In order to update less we can do a "checksum" of the pages being written
    #  and only update those pages which fail.
    #  Almost always, we should only have to update the last page.
    #  Our checksum should be the results of this SQL query:
    #  NOTE THAT: Checksum technique will require rewards to be sorted!
    rewards.sort(key=lambda t: t.order_uid)

    log.info(f"Got {len(rewards)} records.")
    partition_size = 3000  # (~0.73Mb < 1Mb)
    values = list(map(str, rewards))

    log.info(f"Partitioning {len(values)} into chunks of size {partition_size}")
    multi_push_view(
        dune,
        query_file="user_generated/order_rewards_page.sql",
        aggregate_query_file="user_generated/order_rewards.sql",
        base_table_name="cow_order_rewards",
        partitioned_values=[
            values[i : i + partition_size]
            for i in range(0, len(values), partition_size)
        ],
        env=env,
        query_id=ORDER_REWARDS_QUERY,
        # skip=26,
    )


def drop_page_query(env: Environment, page: int) -> str:
    """Dune SQL query to drop order reward page"""
    return (
        open_query(
            os.path.join(QUERY_PATH, "user_generated/drop_order_rewards_page.sql")
        )
        .replace("{{Environment}}", str(env))
        .replace("{{Page}}", str(page))
    )


def drop_page_range(
    dune: DuneAPI, env: Environment, page_from: int, page_to: int
) -> None:
    """Dune SQL query to drop a range of order reward pages from `page_from` to `page_to`"""
    if page_to < page_from:
        log.warning(f"Invalid page range {page_from} to {page_to}")
        return
    query = "\n".join(
        [drop_page_query(env, page) for page in range(page_from, page_to + 1)]
    )
    dune.fetch(
        DuneQuery.from_environment(
            raw_sql=query,
            network=Network.MAINNET,
            name=f"Drop Order Rewards pages {page_from} to {page_to} (inclusive)",
        )
    )


def drop_all_pages(dune: DuneAPI, env: Environment) -> None:
    """
    Drops all User generated views related to order rewards for `env`
    This includes all pages and any aggregate views that depend on them.
    """
    log.info("Dropping all existing dune pages")
    largest_page_query = open_query(
        os.path.join(QUERY_PATH, "user_generated/largest_page.sql")
    ).replace("{{Environment}}", str(env))
    max_page = int(
        dune.fetch(
            DuneQuery.from_environment(
                raw_sql=largest_page_query,
                network=Network.MAINNET,
                name="Order Rewards max page number",
            )
        )[0]["last_page"]
    )
    drop_page_range(dune, env, 0, max_page)


if __name__ == "__main__":
    args = update_args()
    fetch_and_push_order_rewards(
        dune=DuneAPI.new_from_environment(),
        env=args.environment,
        drop_first=args.drop_first,
    )
