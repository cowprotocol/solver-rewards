import pytest
from pytest_mock import MockerFixture
import os

@pytest.fixture(scope="function")
def mock_env(mocker: MockerFixture):
    mocker.patch.dict(
        os.environ, 
        {
        "NETWORK": "gnosis"
        }
    )
