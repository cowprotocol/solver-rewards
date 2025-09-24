import requests
from datetime import datetime
import time
import json

# RPC_URL = "https://mainnet.infura.io/v3/66a67d6489254f9bb99743600b06d6e7"  # Replace with your node RPC URL
# RPC_URL = "https://polygon-mainnet.infura.io/v3/66a67d6489254f9bb99743600b06d6e7"
RPC_URL = "https://base-mainnet.infura.io/v3/66a67d6489254f9bb99743600b06d6e7"
# RPC_URL = "https://arbitrum-mainnet.infura.io/v3/66a67d6489254f9bb99743600b06d6e7"
# RPC_URL = "https://avalanche-mainnet.infura.io/v3/66a67d6489254f9bb99743600b06d6e7"


HEADERS = {"Content-Type": "application/json"}

counter = 0


def datetime_to_timestamp(dt_str):
    return int(datetime.strptime(dt_str, "%Y-%m-%d %H:%M:%S").timestamp())


def get_block_by_number(block_number):
    payload = {
        "jsonrpc": "2.0",
        "method": "eth_getBlockByNumber",
        "params": [hex(block_number), False],
        "id": block_number,
    }
    response = requests.post(RPC_URL, headers=HEADERS, json=payload).json()
    return response["result"]


def get_latest_block_number():
    payload = {"jsonrpc": "2.0", "method": "eth_blockNumber", "params": [], "id": 1}
    response = requests.post(RPC_URL, headers=HEADERS, json=payload).json()
    return int(response["result"], 16)


# Binary search for a block by timestamp
def binary_search_block(target_ts, low=0, high=None):
    if high is None:
        high = get_latest_block_number()

    while low <= high:
        mid = (low + high) // 2
        block = get_block_by_number(mid)
        ts = int(block["timestamp"], 16)
        if ts < target_ts:
            low = mid + 1
        elif ts > target_ts:
            high = mid - 1
        else:
            return mid
    return low


def batch_get_blocks(start_block, end_block, batch_size=50):
    blocks = []
    for i in range(start_block, end_block + 1, batch_size):
        batch = []
        for blk_num in range(i, min(i + batch_size, end_block + 1)):
            batch.append(
                {
                    "jsonrpc": "2.0",
                    "method": "eth_getBlockByNumber",
                    "params": [hex(blk_num), False],
                    "id": blk_num,
                }
            )

        try:
            response = requests.post(
                RPC_URL, headers=HEADERS, data=json.dumps(batch)
            ).json()
        except Exception as e:
            print(
                f"❌ Network or JSON error while requesting blocks {i}-{i + batch_size - 1}: {e}"
            )
            continue

        for res in response:
            if "result" in res and res["result"] is not None:
                blk = res["result"]
                ts = int(blk["timestamp"], 16)
                if start_ts <= ts <= end_ts:
                    blocks.append(
                        (
                            int(blk["number"], 16),
                            datetime.utcfromtimestamp(ts).strftime("%Y-%m-%d %H:%M:%S"),
                        )
                    )
            else:
                error_msg = res.get("error", {}).get("message", "Unknown error")
                print(f"⚠️ Block ID {res.get('id')} failed: {error_msg}")
    return blocks


if __name__ == "__main__":

    START_TIME = "2025-07-01 00:00:00"
    END_TIME = "2025-07-01 00:30:00"
    start_ts = datetime_to_timestamp(START_TIME)
    end_ts = datetime_to_timestamp(END_TIME)
    start_block = binary_search_block(start_ts)
    end_block = binary_search_block(end_ts)

    print(f"Scanning blocks {start_block} to {end_block}")

    results = batch_get_blocks(start_block, end_block)

    for blk, ts in results:
        print(f"Block: {blk}, Timestamp: {ts}")
