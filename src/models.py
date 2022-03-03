import re
from enum import Enum

from web3 import Web3


class Network(Enum):
    MAINNET = 'mainnet'
    GCHAIN = 'gchain'


class Account:

    def __init__(self, address: str):
        if Account._is_valid(address):
            self.address = Web3.toChecksumAddress(address)
        else:
            raise ValueError(f"Invalid Ethereum Address {address}")

    def __str__(self):
        return self.address

    @staticmethod
    def _is_valid(address: str) -> bool:
        if re.match(r'^(0x)?[0-9a-f]{40}$', address, flags=re.IGNORECASE):
            # Check the basic requirements of an address
            return True
        return False
