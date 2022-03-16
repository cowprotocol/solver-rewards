import argparse
from datetime import datetime
from pprint import pprint

from src.dune_analytics import DuneAnalytics, QueryParameter
from src.file_io import File
from src.models import Network
from src.token_list import ALLOWED_TOKEN_LIST_URL, get_trusted_tokens_from_url


def generate_sql_query_for_allowed_token_list(token_list) -> str:
    values = ",".join(
        f"('\\{address[1:]}' :: bytea)" for address in token_list)
    query = f"allow_listed_tokens as (select * from (VALUES {values}) AS t (token)),"
    return query


def prepend_to_sub_query(query, table_to_add):
    if query[0:4].lower() != "with":
        raise ValueError(f"Type {query} does not start with 'with'!")
    return "\n".join(
        [
            query[0:4],
            table_to_add,
            query[5:],
        ]
    )


def add_token_list_table_to_query(original_sub_query: str) -> str:
    """Inserts a the token_list table right after the WITH statement into the sql query"""
    token_list = get_trusted_tokens_from_url(ALLOWED_TOKEN_LIST_URL)
    sql_query_for_allowed_token_list = generate_sql_query_for_allowed_token_list(
        token_list)
    return prepend_to_sub_query(original_sub_query,
                                sql_query_for_allowed_token_list)


def slippage_query(dune: DuneAnalytics) -> str:
    path = "./queries/slippage"
    slippage_sub_query = dune.open_query(
        File("subquery_batchwise_internal_transfers.sql", path).filename())
    select_slippage_query = dune.open_query(
        File("select_slippage_results.sql", path).filename())
    return "\n".join(
        [
            add_token_list_table_to_query(slippage_sub_query),
            select_slippage_query
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
    parser = argparse.ArgumentParser(
        description="Fetch Accounting Period Totals")
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
