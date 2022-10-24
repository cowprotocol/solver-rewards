"""Fetching Risk-Free Batches from Dune Analytics"""
from duneapi.api import DuneAPI
from duneapi.types import DuneQuery, Network, QueryParameter
from duneapi.util import open_query

from src.models import AccountingPeriod


def get_risk_free_batches(dune: DuneAPI, period: AccountingPeriod) -> set[str]:
    """Fetches Risk Free Batches from Dune"""
    results = dune.fetch(
        query=DuneQuery.from_environment(
            raw_sql=open_query("./queries/risk_free_batches.sql"),
            network=Network.MAINNET,
            name="Risk Free Batches",
            parameters=[
                QueryParameter.date_type("StartTime", period.start),
                QueryParameter.date_type("EndTime", period.end),
            ],
        )
    )
    return {row["tx_hash"].lower() for row in results}
