import argparse
from datetime import datetime
from pprint import pprint

from src.dune_analytics import DuneAnalytics, QueryParameter
from src.file_io import File
from src.models import Network


def slippage_query(dune: DuneAnalytics) -> str:
    path = "./queries/slippage"
    slippage_subquery = File("subquery_batchwise_internal_transfers.sql", path)
    select_slippage = File("select_slippage_results.sql", path)
    return "\n".join(
        [
            dune.open_query(slippage_subquery.filename()),
            dune.open_query(select_slippage.filename())
        ]
    )


def get_period_slippage(
        dune: DuneAnalytics,
        period_start: datetime,
        period_end: datetime,
) -> list:
    return dune.fetch(
        query_str=slippage_query(dune),
        network=Network.MAINNET,
        name='Slippage Accounting',
        parameters=[
            QueryParameter.date_type("StartTime", period_start),
            QueryParameter.date_type("EndTime", period_end),
            QueryParameter.text_type("TxHash", '0x'),
            QueryParameter.text_type("ResultTable", "results")
        ]
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

    slippage_for_period = get_period_slippage(
        dune=dune_connection,
        period_start=datetime.strptime(args.start, "%Y-%m-%d"),
        period_end=datetime.strptime(args.end, "%Y-%m-%d"),
    )

    pprint(slippage_for_period)
