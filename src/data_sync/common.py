"""Shared methods between both sync scripts."""

from datetime import datetime, timezone
from typing import List, Tuple

from dateutil.relativedelta import (
    relativedelta,
)  # dateutil is currently not explicitly required in requirement.in, only installed via dune
from web3 import Web3

from src.logger import set_log

log = set_log(__name__)


def compute_time_range(
    start_time: datetime, end_time: datetime
) -> list[tuple[datetime, datetime]]:
    """Computes (list of) time ranges from input parameters."""
    assert start_time < end_time, "start_time must be strictly smaller than end_time"

    if end_time <= datetime(start_time.year, start_time.month, 1).replace(
        tzinfo=timezone.utc
    ) + relativedelta(months=1):
        return [(start_time, end_time)]

    raise NotImplementedError(
        "multiple month not implemented yet. call multiple times instead."
    )


def compute_block_range(
    start_time: datetime, end_time: datetime, node: Web3
) -> tuple[int, int]:
    """Computes a block range from start and end time.
    The convention for block ranges is to be inclusive, while the end time is exclusive.
    """
    latest_block = node.eth.get_block("finalized")
    latest_block_time = datetime.fromtimestamp(
        latest_block["timestamp"], tz=timezone.utc
    )

    assert (
        start_time < latest_block_time
    ), "start time must be smaller than latest block time"

    start_block = find_block_with_timestamp(node, start_time.timestamp())
    if latest_block_time < end_time:
        end_block = int(latest_block["number"])
    else:
        end_block = find_block_with_timestamp(node, end_time.timestamp()) - 1

    return start_block, end_block


def find_block_with_timestamp(node: Web3, time_stamp: float) -> int:
    """
    This implements binary search and returns the smallest block number
    whose timestamp is at least as large as the time_stamp argument passed in the function
    """
    end_block_number = int(node.eth.get_block("finalized")["number"])
    start_block_number = 1
    close_in_seconds = 30

    while True:
        mid_block_number = (start_block_number + end_block_number) // 2
        block = node.eth.get_block(mid_block_number)
        block_time = block["timestamp"]
        difference_in_seconds = int((time_stamp - block_time))

        if abs(difference_in_seconds) < close_in_seconds:
            break

        if difference_in_seconds < 0:
            end_block_number = mid_block_number - 1
        else:
            start_block_number = mid_block_number + 1

    ## we now brute-force to ensure we have found the right block
    for b in range(mid_block_number - 200, mid_block_number + 200):
        block = node.eth.get_block(b)
        block_time_stamp = block["timestamp"]
        if block_time_stamp >= time_stamp:
            return int(block["number"])
    # fallback in case correct block number hasn't been found
    # in that case, we will include some more blocks than necessary
    return mid_block_number + 200


def compute_block_and_month_range(  # pylint: disable=too-many-locals
    node: Web3, recompute_previous_month: bool
) -> Tuple[List[Tuple[int, int]], List[str]]:
    """
    This determines the block range and the relevant months
    for which we will compute and upload data on Dune.
    """
    # The function first a list of block ranges, followed by a list of
    # # months. Block ranges are stored as (start_block, end_block) pairs,
    # and are meant to be interpreted as closed intervals.
    # Moreover, we assume that the job runs at least once every 24h
    # Because of that, if it is the first day of month, we also
    # compute the previous month's table just to be on the safe side

    latest_finalized_block = node.eth.get_block("finalized")

    current_month_end_block = int(latest_finalized_block["number"])
    current_month_end_timestamp = latest_finalized_block["timestamp"]

    current_month_end_datetime = datetime.fromtimestamp(
        current_month_end_timestamp, tz=timezone.utc
    )
    current_month_start_datetime = datetime(
        current_month_end_datetime.year, current_month_end_datetime.month, 1, 00, 00
    )
    current_month_start_timestamp = current_month_start_datetime.replace(
        tzinfo=timezone.utc
    ).timestamp()

    current_month_start_block = find_block_with_timestamp(
        node, current_month_start_timestamp
    )

    current_month = (
        f"{current_month_end_datetime.year}_{current_month_end_datetime.month}"
    )
    ## in case the month is 1-9, we add a "0" prefix, so that we have a fixed-length representation
    ## e.g., 2024-12, 2024-01
    if len(current_month) < 7:
        current_month = current_month[:5] + "0" + current_month[5]
    months_list = [current_month]
    block_range = [(current_month_start_block, current_month_end_block)]
    if current_month_end_datetime.day == 1 or recompute_previous_month:
        if current_month_end_datetime.month == 1:
            previous_month = f"{current_month_end_datetime.year - 1}_12"
            previous_month_start_datetime = datetime(
                current_month_end_datetime.year - 1, 12, 1, 00, 00
            )
        else:
            previous_month = f"""{current_month_end_datetime.year}_
                {current_month_end_datetime.month - 1}
            """
            if len(previous_month) < 7:
                previous_month = previous_month[:5] + "0" + previous_month[5]
            previous_month_start_datetime = datetime(
                current_month_end_datetime.year,
                current_month_end_datetime.month - 1,
                1,
                00,
                00,
            )
        months_list.append(previous_month)
        previous_month_start_timestamp = previous_month_start_datetime.replace(
            tzinfo=timezone.utc
        ).timestamp()
        previous_month_start_block = find_block_with_timestamp(
            node, previous_month_start_timestamp
        )
        previous_month_end_block = current_month_start_block - 1
        block_range.append((previous_month_start_block, previous_month_end_block))

    return block_range, months_list
