import unittest

from web3 import Web3
from dune_client.types import Address
from safe_eth.safe.multi_send import MultiSendTx, MultiSendOperation
import pytest

from src.models.overdraft import Overdraft
from src.config import OverdraftConfig, Network
from src.models.accounting_period import AccountingPeriod
from src.abis.load import overdraftsmanager
from tests.constants import (
    ALL_NETWORKS,
    OVERDRAFTS_CONTRACT_ADDRESS_LENS,
    OVERDRAFTS_CONTRACT_ADDRESS_NOT_LENS,
    DUMMY_REWARDS_ADDRESS_1,
    DUMMY_SOLVER_NAME_1,
)


@pytest.mark.parametrize("_network", ALL_NETWORKS)
def test_multisend_tx(_network, monkeypatch):
    contract = overdraftsmanager()
    monkeypatch.setenv("NETWORK", _network)
    for _wei in [0, 1, 100, 123456789, 1000000000000000000, 999999000000000000000000]:
        for start, length in [("1999-01-01", 7), ("2025-10-07", 7), ("2025-10-7", 3)]:
            period = AccountingPeriod(start=start, length_days=length)
            overdraft = Overdraft(
                period=period,
                account=Address(DUMMY_REWARDS_ADDRESS_1),
                name=DUMMY_SOLVER_NAME_1,
                wei=_wei,
            )
            multisendtx = overdraft.as_multisend_tx()
            assert isinstance(multisendtx, MultiSendTx)
            assert multisendtx.value == 0
            data = contract.encode_abi(
                abi_element_identifier="addOverdraft",
                args=[Web3.to_checksum_address(DUMMY_REWARDS_ADDRESS_1), _wei],
            )
            assert multisendtx.data == Web3.to_bytes(hexstr=data)
            match _network:
                case (
                    Network.MAINNET
                    | Network.GNOSIS
                    | Network.ARBITRUM_ONE
                    | Network.BASE
                    | Network.AVALANCHE
                    | Network.POLYGON
                    | Network.BNB
                    | Network.LINEA
                ):
                    assert multisendtx.to == Web3.to_checksum_address(
                        OVERDRAFTS_CONTRACT_ADDRESS_NOT_LENS
                    )
                case Network.LENS:
                    assert multisendtx.to == Web3.to_checksum_address(
                        OVERDRAFTS_CONTRACT_ADDRESS_LENS
                    )
