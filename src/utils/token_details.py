"""
Very basic Token Info Fetcher that gets token decimals
"""
import functools
import logging.config
from duneapi.types import Address
from web3 import Web3

from src.constants import ERC20_ABI, NODE_URL


log = logging.getLogger(__name__)
logging.config.fileConfig(fname="logging.conf", disable_existing_loggers=False)


@functools.cache
def get_token_decimals(address: str | Address) -> int:
    """Fetches Token Decimals and caches results by address"""
    # This requires a real web3 connection
    log.info(f"fetching decimals for token {address}")
    if isinstance(address, Address):
        checksum_address = Web3.toChecksumAddress(address.address)
    else:
        checksum_address = Web3.toChecksumAddress(address)

    token_info = Web3(Web3.HTTPProvider(NODE_URL)).eth.contract(
        address=checksum_address, abi=ERC20_ABI
    )
    # This "trick" is because of the unknown type returned from the contract call.
    token_decimals: int = token_info.functions.decimals().call()
    return token_decimals
