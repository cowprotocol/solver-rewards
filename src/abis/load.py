"""Basic Contract ABI loader (from json files)"""
import json
import os
from enum import Enum
from pathlib import Path
from typing import Any, Optional

from eth_typing.evm import ChecksumAddress
from typing_extensions import Type
from web3 import Web3
from web3.contract import Contract

from src.constants import PROJECT_ROOT
from src.logger import set_log

ABI_PATH = PROJECT_ROOT / Path("src/abis")

WETH9_ADDRESS = Web3().toChecksumAddress("0xc02aaa39b223fe8d0a0e5c4f27ead9083c756cc2")
# web3.eth.contract returns this ugly type,
# probably for backwards compatibility with old python versions
ContractInterface = Type[Contract] | Contract

log = set_log(__name__)


class IndexedContract(Enum):
    """Contracts with abis contained in project"""

    ERC20 = "erc20"
    WETH9 = "weth9"

    def filename(self) -> str:
        """The abi filename"""
        return f"{self.value}.json"

    def filepath(self) -> str:
        """Absolute path to abi file"""
        return os.path.join(ABI_PATH, self.filename())

    def load_contract_abi(self) -> Any:
        """Loads a contract abi from json file"""
        with open(self.filepath(), "r", encoding="utf-8") as file:
            return json.load(file)

    def get_contract(
        self, web3: Optional[Web3], address: Optional[ChecksumAddress]
    ) -> ContractInterface:
        """Loads ContractInterface instance from abi and optional"""
        abi = self.load_contract_abi()
        if not web3:
            # Use dummy web3
            log.warning(
                "Using a fallback (dummy) web3 instance with no actual connection!"
            )
            web3 = Web3()
        if address:
            return web3.eth.contract(address, abi=abi)
        return web3.eth.contract(abi=abi)


# The following methods are merely convenience methods so that users
# don't have to import a bunch of stuff to get the contract then want


def weth9(web3: Optional[Web3] = None) -> ContractInterface:
    """Returns an instance of WETH9 Contract"""
    return IndexedContract.WETH9.get_contract(web3, WETH9_ADDRESS)


def erc20(
    web3: Optional[Web3] = None, address: Optional[ChecksumAddress] = None
) -> ContractInterface:
    """
    Returns an instance of the ERC20 Contract when address provided
    Generic ERC20Interface otherwise.
    """
    return IndexedContract.ERC20.get_contract(web3, address)
