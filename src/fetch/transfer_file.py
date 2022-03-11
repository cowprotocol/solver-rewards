import argparse
from dataclasses import dataclass
from datetime import datetime
from typing import Optional

from src.dune_analytics import DuneAnalytics, QueryParameter
from src.file_io import File, write_to_csv
from src.models import Network, Address


@dataclass
class Transfer:
    """Total amount reimbursed for accounting period"""
    token_type: str
    token_address: Optional[Address]
    receiver: Address
    # safe-airdrop uses float amounts!
    amount: float

    def __init__(self, token_type, token_address, receiver, amount):
        self.token_type = token_type
        self.token_address = Address(token_address) if token_address else None
        self.receiver = Address(receiver)
        self.amount = float(amount)


def get_transfers(
        dune: DuneAnalytics,
        period_start: datetime,
        period_end: datetime
) -> list[Transfer]:
    data_set = dune.fetch(
        query_str=dune.open_query("./queries/period_transfers.sql"),
        network=Network.MAINNET,
        name="Period Transfers",
        parameters=[
            QueryParameter.date_type("StartTime", period_start),
            QueryParameter.date_type("EndTime", period_end),
        ])
    return [
        Transfer(
            token_type=row['token_type'],
            token_address=row['token_address'] or "",
            receiver=row['receiver'],
            amount=row['amount'],
        )
        for row in data_set
    ]


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

    transfers = get_transfers(
        dune=dune_connection,
        period_start=datetime.strptime(args.start, "%Y-%m-%d"),
        period_end=datetime.strptime(args.end, "%Y-%m-%d"),
    )

    outfile = File(name=f"transfers-{args.start}-to-{args.end}.csv")
    write_to_csv(
        data_list=transfers,
        outfile=File(name=f"transfers-{args.start}-to-{args.end}.csv"),
    )
