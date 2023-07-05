"""
Very basic Token Info Fetcher that gets token decimals
"""
import functools
import logging.config

from dune_client.types import Address
from web3 import Web3

from src.abis.load import erc20
from src.constants import LOG_CONFIG_FILE

log = logging.getLogger(__name__)

logging.config.fileConfig(
    fname=LOG_CONFIG_FILE.absolute(), disable_existing_loggers=False
)


@functools.cache
def get_token_decimals(web3: Web3, address: str | Address) -> int:
    """Fetches Token Decimals and caches results by address"""
    # This requires a real web3 connection
    log.info(f"fetching decimals for token {address}")
    if isinstance(address, Address):
        checksum_address = web3.to_checksum_address(address.address)
    else:
        checksum_address = web3.to_checksum_address(address)
    token = erc20(web3, checksum_address)
    # This "trick" is because of the unknown type returned from the contract call.
    token_decimals: int = token.functions.decimals().call()
    return token_decimals
