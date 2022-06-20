from enum import Enum
from typing import Any

import psycopg2
from duneapi.api import DuneAPI
from duneapi.types import DuneQuery
from psycopg2._psycopg import connection, cursor
from psycopg2.extras import RealDictCursor, RealDictRow


class ConnectionType(Enum):
    LOCAL = "local"
    REMOTE = "remote"


class DBRouter:
    def __init__(self, connection_type: ConnectionType) -> None:
        self.route = connection_type
        self.conn, self.cur, self.dune = None, None, None

        if self.route == ConnectionType.LOCAL:
            self.conn, self.cur = connect_and_populate_db()
        elif self.route == ConnectionType.REMOTE:
            self.dune = DuneAPI.new_from_environment()
        else:
            raise ValueError("Must provide valid connection type")

    def fetch(self, query: DuneQuery) -> list[dict[str, str]]:
        # TODO - make class DBQuery; using DuneQuery for REMOTE and rawSQL for LOCAL
        if self.route == ConnectionType.LOCAL:
            return execute_dune_query(query, self.cur)
        elif self.route == ConnectionType.REMOTE:
            return self.dune.fetch(query)

    def close(self):
        if self.route == ConnectionType.LOCAL:
            self.conn.close()
        elif self.route == ConnectionType.REMOTE:
            # Here we could log out, but duneapi doesn't have such a feature.
            # Could also delete the dune connection..
            pass


def connect() -> connection:
    return psycopg2.connect(
        host="localhost",
        port=5432,
        database="postgres",
        user="postgres",
        password="postgres",
    )


# TODO 1. pass populate_db script as optional parameter.
#  2. Separate create schema and table commands
def connect_and_populate_db() -> tuple[connection, cursor]:
    conn = connect()
    cur = conn.cursor(cursor_factory=RealDictCursor)
    # Populate DB with sample data
    populate_from(cur, "./populate_db.sql")
    return conn, cur


def populate_from(cur: cursor, create_filename: str):
    # Populate DB with sample data
    with open(create_filename, "r", encoding="utf-8") as file:
        cur.execute(file.read())


def fill_parameterized_query(dune_query: DuneQuery):
    """
    Used for unit testing Dune queries on local database
    Fills the parameterized SQL template of the Dune Query
    with the parameter values.
    """
    filled_query = dune_query.raw_sql
    for parameter in dune_query.parameters:
        value_str = parameter.to_dict()["value"]
        filled_query = filled_query.replace(f"{{{{{parameter.key}}}}}", value_str)
    return filled_query


def execute_dune_query(dune_query: DuneQuery, cur: cursor):
    """Transforms DuneQuery into raw SQL and executes on the local database"""
    local_query = fill_parameterized_query(dune_query)
    cur.execute(local_query)
    results: list[RealDictRow] = cur.fetchall()
    parsed_results: list[dict[str, str]] = []
    for rec in results:
        processed_record = {}
        for key, val in rec.items():
            if isinstance(val, memoryview):
                val = f"\\x{val.hex()}"
            processed_record[key] = val
        parsed_results.append(processed_record)

    return parsed_results
