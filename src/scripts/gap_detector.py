"""
Gap detection script for finding missing transaction hashes of settlements.
Uses a form of binary search to minimize/reduce API requests.
"""
from __future__ import annotations
import argparse
import os
from dataclasses import dataclass

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
MAX_QUERYABLE_HASH_SET = 500
MAX_QUERYABLE_BLOCK_RANGE = 10000


@dataclass
class BatchCounts:
    """Data class holding batch number counts with a few elementary helper methods"""

    dune: int
    database: int

    def diff(self) -> int:
        """Absolute difference between counts (ideally zero)"""
        return abs(self.dune - self.database)

    def max(self) -> int:
        """Larger of the two batch counts"""
        return max(self.dune, self.database)


@dataclass
class SourceDiff:
    """Dataclass of set differences"""

    dune_not_db: set[str]
    db_not_dune: set[str]

    @classmethod
    def from_pair(cls, dune: set[str], database: set[str]) -> SourceDiff:
        """constructor from two sets"""
        return cls(dune_not_db=dune - database, db_not_dune=database - dune)

    @classmethod
    def default(cls) -> SourceDiff:
        """Empty object"""
        return cls(dune_not_db=set(), db_not_dune=set())

    def union(self, other: SourceDiff) -> SourceDiff:
        """component wise set union"""
        return SourceDiff(
            dune_not_db=self.dune_not_db.union(other.dune_not_db),
            db_not_dune=self.db_not_dune.union(other.db_not_dune),
        )

    def is_empty(self) -> bool:
        """equivalent to is default object with both empty components"""
        return not self.db_not_dune and not self.dune_not_db


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

    def get_batch_counts(
        self,
        start: int,
        end: int,
    ) -> BatchCounts:
        """
        This function acts as a quick comparison between data sources for a block range.
        The assumption is that if the number of batches between a certain block range agrees,
        between the two sources then they are correct. If a difference is detected, one could
        drill deeper and compare the set of transaction hashes. The transaction hash comparison
        would also reveal any other types of disagreement that the count does not catch.
        """
        dune_count = self.dune_df(DUNE_COUNT_QUERY_ID, start, end)
        db_count = self.db_df(DB_COUNT_QUERY, start, end)
        return BatchCounts(
            dune=int(dune_count["batches"][0]), database=int(db_count["batches"][0])
        )

    def find_missing(
        self,
        start: int,
        end: int,
    ) -> SourceDiff:
        """
        A recursive binary search, returning any disagreement
        in transaction hash sets (between dune and database) for a given block range.
        """
        print("Inspecting Block Range...", start, end)
        batch_counts = self.get_batch_counts(start, end)
        print(batch_counts)
        if batch_counts.diff() == 0:
            # Nothing missing here!
            print("counts agree on", start, end)
            return SourceDiff.default()

        if (
            end - start < MAX_QUERYABLE_BLOCK_RANGE
            or batch_counts.max() < MAX_QUERYABLE_HASH_SET
        ):
            # At this point the query set is small enough to fetch
            return SourceDiff.from_pair(
                dune=set(self.dune_df(DUNE_HASH_QUERY_ID, start, end)["tx_hash"]),
                database=set(self.db_df(DB_HASH_QUERY, start, end)["tx_hash"]),
            )

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
    missing = gap_detector.find_missing(
        start=args.start,
        end=int(
            dune_client.refresh(
                Query(name="Latest Dune Block", query_id=2603762)
            ).get_rows()[0]["latest_block"]
        ),
    )

    print(missing)
