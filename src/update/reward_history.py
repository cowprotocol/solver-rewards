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

from dataclasses import dataclass
from typing import Optional

from duneapi.api import DuneAPI
from pandas import DataFrame

from src.logger import set_log
from src.pg_client import pg_hex2bytea, DualEnvDataframe
from src.update.utils import Environment, update_args
from src.utils.query_file import open_query

log = set_log(__name__)


@dataclass
class OrderRewards:
    """OrderReward values"""

    solver: str
    tx_hash: str
    order_uid: str
    surplus_fee: int
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
                surplus_fee=int(row["surplus_fee"]),
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
        return f"('{order_id}','{solver}','{tx_hash}',{self.surplus_fee},{self.amount},{safe})"


def fetch_and_push_order_rewards(dune: DuneAPI, env: Environment) -> None:
    """Fetches and parses Order Rewards from Orderbook, pushes them to Dune."""
    log.info("Fetching and Merging Orderbook Rewards")
    rewards = OrderRewards.from_dataframe(
        DualEnvDataframe.get_orderbook_rewards(
            start_block="15771267",
            end_block="999999999",  # 320 years from now with 12-second block times
        )
    )
    log.info(f"Got {len(rewards)} records.")
    dune.push_view(
        table_name=f"cow_order_rewards_{env}",
        select_template=open_query("user_generated/order_rewards_template.sql"),
        values=list(map(str, rewards)),
    )


def run() -> None:
    """Logic for main entry of this script"""
    args = update_args()
    fetch_and_push_order_rewards(
        dune=DuneAPI.new_from_environment(),
        env=args.environment,
    )


if __name__ == "__main__":
    run()
