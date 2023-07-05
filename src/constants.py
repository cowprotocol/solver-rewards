"""Project Global Constants. """
import os
from pathlib import Path

from dotenv import load_dotenv
from dune_client.types import Address
from gnosis.eth.ethereum_network import EthereumNetwork
from web3 import Web3


COW_TOKEN_ADDRESS = Address("0xDEf1CA1fb7FBcDC777520aa7f396b4E015F497aB")

PROJECT_ROOT = Path(__file__).parent.parent
FILE_OUT_DIR = PROJECT_ROOT / Path("out")
LOG_CONFIG_FILE = PROJECT_ROOT / Path("logging.conf")
QUERY_PATH = PROJECT_ROOT / Path("queries")
DASHBOARD_PATH = PROJECT_ROOT / Path("dashboards/solver-rewards-accounting")

DOCS_URL = (
    "https://www.notion.so/cownation/Solver-Payouts-3dfee64eb3d449ed8157a652cc817a8c"
)

# Things requiring network
load_dotenv()
ENV = os.environ
SAFE_ADDRESS = Web3.to_checksum_address(
    ENV.get("SAFE_ADDRESS", "0xA03be496e67Ec29bC62F01a428683D7F9c204930")
)
# Found this exposed infura key on https://rpc.info/
INFURA_KEY = ENV.get("INFURA_KEY", "9aa3d95b3bc440fa88ea12eaa4456161")
NETWORK_STRING = ENV.get("NETWORK", "mainnet")
NODE_URL = f"https://{NETWORK_STRING}.infura.io/v3/{INFURA_KEY}"
NETWORK = {
    "mainnet": EthereumNetwork.MAINNET,
    "gnosis": EthereumNetwork.GNOSIS,
    "goerli": EthereumNetwork.GOERLI,
}[NETWORK_STRING]
SHORT_NAME = {
    "mainnet": "eth",
    "rinkeby": "rin",
    "gnosis": "gno",
    "goerli": "gor",
}[NETWORK_STRING]

CSV_APP_HASH = "Qme49gESuwpSvwANmEqo34yfCkzyQehooJ5yL7aHmKJnpZ"
SAFE_URL = "https://app.safe.global"
AIRDROP_URL = (
    f"{SAFE_URL}/{SHORT_NAME}:{SAFE_ADDRESS}"
    f"/apps?appUrl=https://cloudflare-ipfs.com/ipfs/{CSV_APP_HASH}/"
)
SAFE_URL = f"{SAFE_URL}/{SHORT_NAME}:{SAFE_ADDRESS}/transactions/queue"

# Real Web3 Instance
web3 = Web3(Web3.HTTPProvider(NODE_URL))
