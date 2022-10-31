"""Fetches Solver ETH Spent from Dune for Accounting Period"""
from duneapi.api import DuneAPI
from duneapi.types import DuneQuery, QueryParameter, Network
from duneapi.util import open_query

from src.models.accounting_period import AccountingPeriod
from src.models.transfer import Transfer

from src.utils.query_file import query_file


def get_eth_spent(dune: DuneAPI, period: AccountingPeriod) -> list[Transfer]:
    """
    Fetches ETH spent on successful settlements by all solvers during `period`
    """
    query = DuneQuery.from_environment(
        raw_sql=open_query(query_file("eth_spent.sql")),
        network=Network.MAINNET,
        name="ETH Reimbursement",
        parameters=[
            QueryParameter.date_type("StartTime", period.start),
            QueryParameter.date_type("EndTime", period.end),
        ],
    )
    return [Transfer.from_dict(t) for t in dune.fetch(query)]
