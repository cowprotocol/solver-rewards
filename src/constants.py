"""Project Global Constants. """
import json
import os

import logging.config
import requests.exceptions
from dotenv import load_dotenv
from duneapi.types import Address
from eth_typing.ethpm import URI
from gnosis.eth.ethereum_client import EthereumClient
from gnosis.eth.ethereum_network import EthereumNetwork
from web3 import Web3

load_dotenv()

log = logging.getLogger(__name__)
logging.config.fileConfig(fname="logging.conf", disable_existing_loggers=False)

# Things requiring network
# TODO - this is such a mess!
network_string = os.environ.get("NETWORK", "mainnet")
NETWORK = {
    "mainnet": EthereumNetwork.MAINNET,
    "rinkeby": EthereumNetwork.RINKEBY,
    "gnosis": EthereumNetwork.XDAI,
    "goerli": EthereumNetwork.GOERLI,
}[network_string]

NODE_URL = f"https://{network_string}.infura.io/v3/{os.environ.get('INFURA_KEY')}"
try:
    ETH_CLIENT = EthereumClient(URI(NODE_URL))
except requests.exceptions.InvalidURL:
    # Use default client (i.e. localhost)
    ETH_CLIENT = EthereumClient()

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
ERC20_TOKEN = w3.eth.contract(abi=ERC20_ABI)
COW_SAFE_ADDRESS = w3.toChecksumAddress("0xA03be496e67Ec29bC62F01a428683D7F9c204930")
COW_TOKEN_ADDRESS = Address("0xDEf1CA1fb7FBcDC777520aa7f396b4E015F497aB")
