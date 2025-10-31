import unittest

from dune_client.types import Address
from eth_typing import HexStr
from safe_eth.safe.multi_send import MultiSendTx, MultiSendOperation
import pytest
from web3 import Web3

from src.config import OverdraftConfig, Network
from tests.constants import (
    ALL_NETWORKS,
    OVERDRAFTS_CONTRACT_ADDRESS_LENS,
    OVERDRAFTS_CONTRACT_ADDRESS_NOT_LENS,
)


@pytest.mark.parametrize("network", ALL_NETWORKS)
def test_config_serializes(network, monkeypatch):
    network = Network(network)
    overdraft_config = OverdraftConfig.from_network(network)
    match network:
        case (
            Network.MAINNET
            | Network.GNOSIS
            | Network.ARBITRUM_ONE
            | Network.BASE
            | Network.AVALANCHE
            | Network.POLYGON
            | Network.BNB
        ):
            assert overdraft_config.contract_address == Address(
                OVERDRAFTS_CONTRACT_ADDRESS_NOT_LENS
            )
        case Network.LENS:
            assert overdraft_config.contract_address == Address(
                OVERDRAFTS_CONTRACT_ADDRESS_LENS
            )
