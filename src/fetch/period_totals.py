"""
Script to query and display total funds distributed for specified accounting period.
"""
from dataclasses import dataclass
from pprint import pprint

from duneapi.api import DuneAPI
from duneapi.types import QueryParameter, DuneQuery, Network
from duneapi.util import open_query

from src.models import AccountingPeriod
from src.utils.query_file import dashboard_file
from src.utils.script_args import generic_script_init


@dataclass
class PeriodTotals:
    """Total amount reimbursed for accounting period"""

    period: AccountingPeriod
    execution_cost_eth: int
    cow_rewards: int
    realized_fees_eth: int


def get_period_totals(dune: DuneAPI, period: AccountingPeriod) -> PeriodTotals:
    """
    Fetches & Returns Dune Results for accounting period totals.
    """
    query = DuneQuery.from_environment(
        raw_sql=open_query(dashboard_file("period-totals.sql")),
        network=Network.MAINNET,
        name="Accounting Period Totals",
        parameters=[
            QueryParameter.date_type("StartTime", period.start),
            QueryParameter.date_type("EndTime", period.end),
        ],
    )
    data_set = dune.fetch(query)
    assert len(data_set) == 1
    rec = data_set[0]
    return PeriodTotals(
        period=period,
        execution_cost_eth=int(rec["execution_cost_eth"]),
        cow_rewards=int(rec["cow_rewards"]),
        realized_fees_eth=int(rec["realized_fees_eth"]),
    )


if __name__ == "__main__":
    args = generic_script_init(description="Fetch Accounting Period Totals")

    total_for_period = get_period_totals(dune=args.dune, period=args.period)

    pprint(total_for_period)
