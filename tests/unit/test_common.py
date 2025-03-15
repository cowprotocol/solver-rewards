import pytest
from pytest_mock import MockerFixture
import datetime
from src.data_sync.common import (
    partition_time_range, 
    compute_block_range, 
    find_block_with_timestamp)

from web3 import Web3

@pytest.fixture(scope="session")
def times():
    start_time = datetime.datetime.now(tz=datetime.timezone.utc)
    end_time = start_time + datetime.timedelta(seconds=10)
    return{
        "start_time": start_time,
        "end_time": end_time
    }

@pytest.fixture(scope="function")
def mock_node():
    return Web3()

def test_partition_time_range(mocker: MockerFixture):
    start_time = datetime.datetime.now(tz=datetime.timezone.utc)
    end_time = start_time + datetime.timedelta(seconds=10)

    # test that if they are equal or negative the function raises an error
    with pytest.raises(AssertionError):
        partition_time_range(start_time=start_time, end_time=start_time)
    
    with pytest.raises(AssertionError):
        partition_time_range(start_time=start_time, end_time=start_time + datetime.timedelta(seconds=-10))
    
    # end time is not greater than a month
    result = partition_time_range(start_time=start_time, end_time=end_time)
    assert result == [(start_time, end_time)]

    # end time is greater than a month
    result = partition_time_range(start_time=start_time, end_time=end_time + datetime.timedelta(days=60))

    assert len(result) == 3

def test_compute_block_range(mocker: MockerFixture, times, mock_node):
    mock_find_block = mocker.patch("src.data_sync.common.find_block_with_timestamp", side_effect=[200, 400])
    mock_get_block = mocker.patch.object(mock_node.eth, "get_block", return_value={
        "number": 400,
        "timestamp": times["end_time"].timestamp()})
    results = compute_block_range(
        start_time=times["start_time"], 
        end_time=times["end_time"], 
        node=mock_node)
    
    assert mock_find_block.call_count == 2
    mock_get_block.assert_called_once()
    assert results.block_from == 200
    assert results.block_to == 399

def test_find_block_with_timestamp(mocker: MockerFixture, mock_node, times):
    end_timestamp = times["end_time"].timestamp()
    mock_get_block = mocker.patch.object(mock_node.eth, "get_block", return_value={
        "number": 400,
        "timestamp": end_timestamp})
    results = find_block_with_timestamp(node=mock_node, time_stamp=end_timestamp)
    assert results == 400
    assert mock_get_block.call_count == 3
