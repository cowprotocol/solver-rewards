"""
Script to query and display total funds distributed for specified accounting period.
"""
import argparse
from dataclasses import dataclass
from datetime import datetime
from pprint import pprint

from src.dune_analytics import DuneAnalytics, QueryParameter
from src.models import Network


@dataclass
class PeriodTotals:
    """Total amount reimbursed for accounting period"""
    # Block numbers for accounting period boundaries
    # TODO - introduce AccountingPeriod class (data class)
    period_start: datetime
    period_end: datetime
    execution_cost_eth: int
    cow_rewards: int
    realized_fees_eth: int


def get_period_totals(
        dune: DuneAnalytics,
        period_start: datetime,
        period_end: datetime
) -> PeriodTotals:
    """
    Fetches & Returns Dune Results for accounting period totals.
    """
    data_set = dune.fetch(
        query_filepath="./queries/period_totals.sql",
        network=Network.MAINNET,
        name="Accounting Period Totals",
        parameters=[
            QueryParameter.date_type("StartTime", period_start),
            QueryParameter.date_type("EndTime", period_end),
        ])
    assert len(data_set) == 1
    rec = data_set[0]
    return PeriodTotals(
        period_start=period_start,
        period_end=period_end,
        execution_cost_eth=rec['execution_cost_eth'],
        cow_rewards=rec['cow_rewards'],
        realized_fees_eth=rec['realized_fees_eth'],
    )


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="Fetch Accounting Period Totals")
    parser.add_argument(
        "--start",
        type=str,
        help="Accounting Period Start",
        required=True
    )
    parser.add_argument(
        "--end",
        type=str,
        help="Accounting Period End",
        required=True
    )
    args = parser.parse_args()

    dune_connection = DuneAnalytics.new_from_environment()

    total_for_period = get_period_totals(
        dune=dune_connection,
        period_start=datetime.strptime(args.start, "%Y-%m-%d"),
        period_end=datetime.strptime(args.end, "%Y-%m-%d"),
    )

    pprint(total_for_period)
