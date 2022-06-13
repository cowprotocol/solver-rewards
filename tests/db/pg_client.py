from dotenv import load_dotenv
import psycopg2
from psycopg2._psycopg import cursor
from duneapi.types import DuneQuery


def connect():
    load_dotenv()
    conn = psycopg2.connect(
        host="localhost",
        port=5432,
        database="postgres",
        user="postgres",
        password="postgres",
    )
    return conn


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
    results = cur.fetchall()
    return results
