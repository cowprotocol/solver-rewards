"""
Script to query and display total funds distributed for specified accounting period.
"""
from dataclasses import dataclass
from pprint import pprint

from src.dune_analytics import DuneAnalytics, QueryParameter
from src.models import AccountingPeriod, Network
from src.utils.script_args import generic_script_init


@dataclass
class PeriodTotals:
    """Total amount reimbursed for accounting period"""

    period: AccountingPeriod
    execution_cost_eth: int
    cow_rewards: int
    realized_fees_eth: int


def get_period_totals(dune: DuneAnalytics, period: AccountingPeriod) -> PeriodTotals:
    """
    Fetches & Returns Dune Results for accounting period totals.
    """
    data_set = dune.fetch(
        query_str=dune.open_query("./queries/period_totals.sql"),
        network=Network.MAINNET,
        name="Accounting Period Totals",
        parameters=[
            QueryParameter.date_type("StartTime", period.start),
            QueryParameter.date_type("EndTime", period.end),
        ],
    )
    assert len(data_set) == 1
    rec = data_set[0]
    return PeriodTotals(
        period=period,
        execution_cost_eth=rec["execution_cost_eth"],
        cow_rewards=rec["cow_rewards"],
        realized_fees_eth=rec["realized_fees_eth"],
    )


if __name__ == "__main__":
    dune_connection, accounting_period = generic_script_init(
        description="Fetch Accounting Period Totals"
    )

    total_for_period = get_period_totals(dune=dune_connection, period=accounting_period)

    pprint(total_for_period)
