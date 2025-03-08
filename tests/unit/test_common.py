import pytest
from pytest_mock import MockerFixture
import datetime
from src.data_sync.common import partition_time_range

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