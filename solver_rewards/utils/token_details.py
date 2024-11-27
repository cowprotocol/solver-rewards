"""
Very basic Token Info Fetcher that gets token decimals
"""

import functools

from dune_client.types import Address
from web3 import Web3

from solver_rewards.abis.load import erc20
from solver_rewards.logger import set_log

log = set_log(__name__)


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
