"""Project Global Constants. """
import json
import os

from duneapi.types import Address
from dotenv import load_dotenv
from gnosis.eth.ethereum_network import EthereumNetwork
from web3 import Web3

COW_TOKEN_ADDRESS = Address("0xDEf1CA1fb7FBcDC777520aa7f396b4E015F497aB")

COW_PER_BATCH = 50
COW_PER_TRADE = 35

# Things requiring network
load_dotenv()
ENV = os.environ
SAFE_ADDRESS = Web3.toChecksumAddress(
    ENV.get("SAFE_ADDRESS", "0xA03be496e67Ec29bC62F01a428683D7F9c204930")
)
INFURA_KEY = ENV.get("INFURA_KEY")
NETWORK_STRING = ENV.get("NETWORK", "mainnet")
NODE_URL = f"https://{NETWORK_STRING}.infura.io/v3/{INFURA_KEY}"
NETWORK = {
    "mainnet": EthereumNetwork.MAINNET,
    "gnosis": EthereumNetwork.XDAI,
    "goerli": EthereumNetwork.GOERLI,
}[NETWORK_STRING]
SHORT_NAME = {
    "mainnet": "eth",
    "rinkeby": "rin",
    "gnosis": "xdai",
    "goerli": "gor",
}[NETWORK_STRING]

CSV_APP_HASH = "Qme49gESuwpSvwANmEqo34yfCkzyQehooJ5yL7aHmKJnpZ"
AIRDROP_URL = (
    f"https://gnosis-safe.io/app/eth:{SAFE_ADDRESS}"
    f"/apps?appUrl=https://cloudflare-ipfs.com/ipfs/{CSV_APP_HASH}/"
)
SAFE_URL = f"https://gnosis-safe.io/app/{SHORT_NAME}:{SAFE_ADDRESS}/transactions/queue"

# Things requiring dummy Web3 instance
ERC20_ABI = json.loads(
    """[
    {
        "inputs": [
            {"internalType": "address", "name": "recipient", "type": "address"},
            {"internalType": "uint256", "name": "amount", "type": "uint256"}
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
ERC20_TOKEN = Web3().eth.contract(abi=ERC20_ABI)
# Real Web3 Instance
w3 = Web3(Web3.HTTPProvider(NODE_URL))
