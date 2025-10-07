"""Overdraft Class"""

from __future__ import annotations

from dataclasses import dataclass

from dune_client.types import Address
from safe_eth.safe.multi_send import MultiSendOperation, MultiSendTx
from web3 import Web3
from src.abis.load import overdraftsmanager
from src.models.accounting_period import AccountingPeriod

OVERDRAFTS_CONTRACT = overdraftsmanager()


@dataclass
class Overdraft:
    """
    Contains the data for a solver's overdraft;
    Namely, overdraft = |transfer - negative slippage| when the difference is negative
    """

    period: AccountingPeriod
    account: Address
    name: str
    wei: int

    @property
    def eth(self) -> float:
        """Returns amount in units"""
        return self.wei / 10**18

    def as_multisend_tx(self) -> MultiSendTx:
        """Converts Overdraft into encoded MultiSendTx bytes"""
        return MultiSendTx(
            operation=MultiSendOperation.CALL,
            to=Web3.to_checksum_address("0x8Fd67Ea651329fD142D7Cfd8e90406F133F26E8a"),
            value=0,
            data=OVERDRAFTS_CONTRACT.encode_abi(
                abi_element_identifier="addOverdraft",
                args=[Web3.to_checksum_address(self.account.address), self.wei],
            ),
        )

    def __str__(self) -> str:
        return (
            f"Overdraft(solver={self.account} ({self.name}),"
            f"period={self.period},owed={self.eth} native token units)"
        )
