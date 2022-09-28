"""
Fetches the closest block number for a given timestamp from Etherscan API
Ref: https://docs.etherscan.io/api-endpoints/blocks#get-block-number-by-timestamp
"""
import json
import os
import time
from datetime import datetime
from enum import Enum

import requests
from dotenv import load_dotenv

ETHERSCAN_API_URL = "https://api.etherscan.io/api"


class Closest(Enum):
    """
    Meant for telling Etherscan API whether you want the
    first block before or after a given timestamp.
    """

    BEFORE = "before"
    AFTER = "after"


def get_block(when: datetime, closest: Closest) -> int:
    """Fetches ethereum mainnet `closest` block number for a given datetime object"""
    epoch = int(time.mktime(when.timetuple()))
    load_dotenv()
    response = requests.get(
        url=ETHERSCAN_API_URL,
        params=json.dumps(
            {
                "module": "block",
                "action": "getblocknobytime",
                "apikey": os.environ["ETHERSCAN_API_KEY"],
                "timestamp": epoch,
                "closest": closest.value,
            }
        ),
    )
    parsed_response = response.json()
    return int(parsed_response["result"])
