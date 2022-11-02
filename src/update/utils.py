"""
A few project level Enums
"""
import argparse
import os
from enum import Enum

from duneapi.api import DuneAPI
from duneapi.types import QueryParameter, DuneQuery, Network
from duneapi.util import open_query

from src.constants import QUERY_PATH
from src.logger import set_log

log = set_log(__name__)


class Environment(Enum):
    """Enum for Deployment Environments"""

    STAGING = "barn"
    PRODUCTION = "prod"
    TEST = "test"

    def __str__(self) -> str:
        return str(self.value)

    def as_query_param(self) -> QueryParameter:
        """Converts Environment to Dune Query Parameter"""
        return QueryParameter.enum_type(
            "Environment", str(self), [str(e) for e in Environment]
        )


def push_view(  # pylint: disable=too-many-arguments
    dune: DuneAPI,
    query_file: str,
    values: list[str],
    query_params: list[QueryParameter],
    separator: str = ",\n",
) -> None:
    """Pushes a user generated view to Dune Analytics via Legacy API"""
    # TODO - use this in update_appdata_view.py and update/user_retention.py
    file_path = os.path.join(QUERY_PATH, query_file)
    raw_sql = open_query(file_path).replace("{{Values}}", separator.join(values))
    log.info(f"Pushing ~{len(raw_sql.encode('utf-8')) / 10 ** 6:.2f} Mb to Dune.")
    query = DuneQuery.from_environment(
        raw_sql=raw_sql,
        name=query_file,
        parameters=query_params,
        network=Network.MAINNET,
    )
    dune.fetch(query)


def paginated_table_name(table_name: str, env: Environment, page: int) -> str:
    """appends page number to a table name"""
    return f"{table_name}_{env}_page_{page}"


def multi_push_view(  # pylint: disable=too-many-arguments
    dune: DuneAPI,
    query_file: str,
    aggregate_query_file: str,
    base_table_name: str,
    partitioned_values: list[list[str]],
    env: Environment,
    skip: int = 0,
) -> None:
    """
    Pushes the values from a partitioned list to multiple pages of tables,
    then builds a table out of the union of those pages
    """
    log.info(f"Creating {len(partitioned_values)} pages from partitioned list")
    aggregate_tables = []
    for page, chunk in enumerate(partitioned_values):
        table_name = paginated_table_name(base_table_name, env, page)

        if page >= skip:
            log.info(f"Pushing Page {page} to {table_name}")
            push_view(
                dune,
                query_file,
                values=chunk,
                query_params=[
                    QueryParameter.text_type("TableName", table_name),
                    env.as_query_param(),
                ],
            )
        else:
            log.info(f"skipping page {page}")
        aggregate_tables.append(
            f"select {page} as page, * from dune_user_generated.{table_name}"
        )
    # TODO - assert sorted values,
    #  - check if updates are even needed (by making a hash select statement)
    #  - Don't update pages that are unchanged

    # This combines all the pages into a single table.
    push_view(
        dune,
        query_file=aggregate_query_file,
        values=aggregate_tables,
        query_params=[env.as_query_param()],
        separator="\nunion\n",
    )


def update_args() -> argparse.Namespace:
    """Arguments used to pass table environment name"""
    # TODO - it would be a lot easier to pass Environment and an ENV var.
    parser = argparse.ArgumentParser()
    parser.add_argument(
        "-e",
        "--environment",
        type=Environment,
        choices=list(Environment),
        default=Environment.TEST,
    )
    parser.add_argument(
        "-d",
        "--drop-first",
        type=bool,
        default=False,
    )
    return parser.parse_args()
