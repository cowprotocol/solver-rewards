"""Basic Contract ABI loader (from json files)"""
import json
import os
from enum import Enum
from pathlib import Path
from typing import Any, Optional

from eth_typing import ChecksumAddress
from typing_extensions import Type
from web3 import Web3
from web3.contract import Contract

from src.constants import PROJECT_ROOT

ABI_PATH = PROJECT_ROOT / Path("src/abis")

WETH9_ADDRESS = Web3().toChecksumAddress("0xc02aaa39b223fe8d0a0e5c4f27ead9083c756cc2")


class IndexedContract(Enum):
    """Contracts with abis contained in project"""

    ERC20 = "erc20"
    WETH9 = "weth9"

    def filename(self) -> str:
        return str(self.value)


def load_contract_abi(abi_name: str) -> Any:
    """Loads a contract abi from json file"""
    with open(
        os.path.join(ABI_PATH, f"{abi_name}.json"), "r", encoding="utf-8"
    ) as file:
        return json.load(file)


# web3.eth.contract returns this ugly type,
# probably for backwards compatibility with old python versions
ContractInterface = Type[Contract] | Contract


def get_contract(
    address: Optional[ChecksumAddress], c_type: IndexedContract
) -> ContractInterface:
    abi = load_contract_abi(c_type.filename())
    if address:
        return Web3().eth.contract(address, abi=abi)
    return Web3().eth.contract(abi=abi)


# The following methods are merely convenience methods so that users
# don't have to import a bunch of stuff to get the contract then want


def weth9() -> ContractInterface:
    return get_contract(WETH9_ADDRESS, IndexedContract.WETH9)


def erc20(address: Optional[ChecksumAddress] = None) -> ContractInterface:
    return get_contract(address, IndexedContract.ERC20)
