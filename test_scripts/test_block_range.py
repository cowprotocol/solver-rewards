from web3 import Web3
from datetime import datetime, timezone
import sys
from web3.middleware import ExtraDataToPOAMiddleware

# === CONFIGURE ===
NODE_URL = "https://avalanche-mainnet.infura.io/v3/66a67d6489254f9bb99743600b06d6e7"  # Replace with your Ethereum RPC URL

def datetime_to_unix(dt: datetime) -> int:
    if dt.tzinfo is None:
        dt = dt.replace(tzinfo=timezone.utc)
    return int(dt.timestamp())

def binary_search_block(w3, target_ts: int, low: int, high: int, search_start=True) -> int:
    result = None
    while low <= high:
        mid = (low + high) // 2
        mid_ts = w3.eth.get_block(mid)["timestamp"]

        if search_start:
            if mid_ts >= target_ts:
                result = mid
                high = mid - 1
            else:
                low = mid + 1
        else:
            if mid_ts < target_ts:
                result = mid
                low = mid + 1
            else:
                high = mid - 1
    return result

def time_to_block(start_time: datetime, end_time: datetime, node_url: str) -> [int, int]:
    w3 = Web3(Web3.HTTPProvider(node_url))
    w3.middleware_onion.inject(ExtraDataToPOAMiddleware, layer=0)

    if not w3.is_connected():
        raise ConnectionError("Failed to connect to Ethereum node.")

    latest_block = w3.eth.block_number
    start_ts = datetime_to_unix(start_time)
    end_ts = datetime_to_unix(end_time)

    first_block = binary_search_block(w3, start_ts, 0, latest_block, search_start=True)
    last_block = binary_search_block(w3, end_ts, 0, latest_block, search_start=False)

    return [first_block, last_block]

def print_block_info(w3, block_number: int, label: str):
    block = w3.eth.get_block(block_number)
    dt = datetime.utcfromtimestamp(block.timestamp).replace(tzinfo=timezone.utc)
    print(f"{label} block: #{block_number} at {dt.isoformat()}")

if __name__ == "__main__":
    # Sample UTC time range
    start_time = datetime(2025, 7, 1, 0, 0, 0)
    end_time = datetime(2025, 7, 3, 0, 0, 0)

    w3 = Web3(Web3.HTTPProvider(NODE_URL))
    w3.middleware_onion.inject(ExtraDataToPOAMiddleware, layer=0)
    first_block, last_block = time_to_block(start_time, end_time, NODE_URL)

    print_block_info(w3, first_block, "Start")
    print_block_info(w3, last_block, "End")
