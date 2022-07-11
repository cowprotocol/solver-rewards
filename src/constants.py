"""Project Global Constants. """
import json
import os

from dotenv import load_dotenv
from duneapi.types import Address
from web3 import Web3

load_dotenv()

COW_TOKEN_ADDRESS = Address("0xDEf1CA1fb7FBcDC777520aa7f396b4E015F497aB")
# Things requiring network
# TODO - this is such a mess!
network_string = os.environ.get("NETWORK", "mainnet")
NODE_URL = f"https://{network_string}.infura.io/v3/{os.environ.get('INFURA_KEY')}"

# Things requiring Web3 instance
w3 = Web3(Web3.HTTPProvider(NODE_URL))
ERC20_ABI = json.loads(
    """[
    {
        "inputs": [
            {"internalType": "address", "name": "recipient", "type": "address"},
            {"internalType": "uint256", "name": "amount_wei", "type": "uint256"}
        ],
        "name": "transfer",
        "outputs": [{"internalType": "bool", "name": "", "type": "bool"}],
        "stateMutability": "nonpayable",
        "type": "function"
    },
    {
        "constant": true,
        "inputs": [],
        "name": "decimals",
        "outputs": [
          {
            "name": "",
            "type": "uint8"
          }
        ],
        "payable": false,
        "stateMutability": "view",
        "type": "function"
  }
]
"""
)
