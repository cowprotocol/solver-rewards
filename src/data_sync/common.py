"""Shared methods between both sync scripts."""

from datetime import datetime, timezone

from dateutil.relativedelta import (
    relativedelta,
)  # dateutil is currently not explicitly required in requirement.in, only installed via dune
from web3 import Web3

from src.logger import set_log

log = set_log(__name__)


def compute_time_range(
    start_time: datetime, end_time: datetime
) -> list[tuple[datetime, datetime]]:
    """Computes (list of) time ranges from input parameters.
    If both times are from the same month, only [(start_time, end_time)] is returned.
    Otherwise, the range is split into n pieces of the form [(start_time, start_of_month_2),
    (start_of_month_2, start_of_month_3),..., (start_of_month_n, end_time)].
    """
    assert start_time < end_time, "start_time must be strictly smaller than end_time"

    # if there is just one month to consider
    if end_time <= datetime(start_time.year, start_time.month, 1).replace(
        tzinfo=timezone.utc
    ) + relativedelta(months=1):
        return [(start_time, end_time)]

    # if there are multiple month to consider
    next_month_start_time = datetime(start_time.year, start_time.month, 1).replace(
        tzinfo=timezone.utc
    ) + relativedelta(months=1)
    time_range_list = [(start_time, next_month_start_time)]
    while end_time > next_month_start_time + relativedelta(months=1):
        time_range_list.append(
            (next_month_start_time, next_month_start_time + relativedelta(months=1))
        )
        next_month_start_time = next_month_start_time + relativedelta(months=1)
    time_range_list.append((next_month_start_time, end_time))

    return time_range_list


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
