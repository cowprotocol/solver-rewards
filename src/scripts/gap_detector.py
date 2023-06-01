"""
Gap detection script for finding missing transaction hashes of settlements.
Uses a form of binary search to minimize/reduce API requests.
"""
import argparse
import os

import pandas as pd
from pandas import DataFrame
from dune_client.client import DuneClient
from dune_client.query import Query
from dune_client.types import QueryParameter
from dotenv import load_dotenv

from src.pg_client import MultiInstanceDBFetcher

DB_COUNT_QUERY = (
    "select count(*) as batches from settlements "
    "where block_number between {{start}} and {{end}};"
)
DB_HASH_QUERY = (
    "select concat('0x', encode(tx_hash, 'hex')) as tx_hash from settlements "
    "where block_number between {{start}} and {{end}};"
)

DUNE_COUNT_QUERY_ID = 2481826
DUNE_HASH_QUERY_ID = 2532671

JANUARY_2023 = 16308190


class GapDetector:
    """Encapsulates all attributes and functionality of gap detection"""

    def __init__(self, dune: DuneClient, database: MultiInstanceDBFetcher):
        self.dune = dune
        self.database = database

    def dune_df(self, query_id: int, start: int, end: int) -> DataFrame:
        """Executes and fetches dataframe from Dune `query_id`"""
        return pd.read_csv(
            self.dune.refresh_csv(
                Query(
                    query_id=query_id,
                    params=[
                        QueryParameter.number_type("start", start),
                        QueryParameter.number_type("end", end),
                    ],
                )
            ).data
        )

    def db_df(self, query_str: str, start: int, end: int) -> DataFrame:
        """Executes and fetches dataframe for `query_str` from Database"""
        return self.database.exec_query(
            query_str.replace("{{start}}", str(start)).replace("{{end}}", str(end)),
            self.database.connections[0],
        )

    def tx_list_diff(
        self,
        start: int,
        end: int,
    ) -> set[str]:
        """Gets the list of differing transaction hashes between Dune and Database"""
        dune_hashes = set(self.dune_df(DUNE_HASH_QUERY_ID, start, end)["tx_hash"])
        db_hashes = set(self.db_df(DB_HASH_QUERY, start, end)["tx_hash"])
        # TODO - usually its the database missing something (i.e. we assume Dune contains all).
        #  However, we could also return an object that keeps track of what is missing where.
        return dune_hashes.symmetric_difference(db_hashes)

    def count_diff(
        self,
        start: int,
        end: int,
    ) -> int:
        """
        This function acts as a quick comparison between data sources for a block range.
        The assumption is that if the number of batches between a certain block range agrees,
        between the two sources then they are correct. If a difference is detected, one could
        drill deeper and compare the set of transaction hashes. The transaction hash comparison
        would also reveal any other types of disagreement that the count does not catch.
        """
        dune_count = self.dune_df(DUNE_COUNT_QUERY_ID, start, end)
        db_count = self.db_df(DB_COUNT_QUERY, start, end)

        return int(dune_count["batches"][0]) - int(db_count["batches"][0])

    def find_missing(
        self,
        start: int,
        end: int,
    ) -> set[str]:
        """
        A recursive binary search, returning any disagreement
        in transaction hash sets (between dune and database) for a given block range.
        """
        print("Inspecting Block Range...", start, end)
        count_diff = self.count_diff(start, end)
        if count_diff == 0:
            # Nothing missing here!
            print("counts agree on", start, end)
            return set()

        if count_diff < 200:  # TODO - make this configurable.
            # getting down into the trees.
            diff = self.tx_list_diff(start, end)
            print("Diff", diff)
            if diff:
                return diff

        print("count diff", count_diff)
        mid = (start + end) // 2
        # Note that this implementation always prefers left side first.
        return self.find_missing(start, mid).union(self.find_missing(mid + 1, end))


if __name__ == "__main__":
    load_dotenv()
    parser = argparse.ArgumentParser("Batch Gap Detector")
    parser.add_argument(
        "--start",
        type=int,
        help="Block number to start the search for",
        default=JANUARY_2023,
    )
    args = parser.parse_args()

    dune_client = DuneClient(os.environ["DUNE_API_KEY"])
    gap_detector = GapDetector(
        dune=dune_client,
        database=MultiInstanceDBFetcher(db_urls=[os.environ["DB_URL"]]),
    )
    gap_detector.find_missing(
        start=args.start,
        end=int(
            dune_client.refresh(
                Query(
                    name="Sync Lag",
                    query_id=2261565,
                    params=[
                        QueryParameter.text_type("table_name", "raw_internal_imbalance")
                    ],
                )
            ).get_rows()[0]["last_sync_block"]
        ),
    )
