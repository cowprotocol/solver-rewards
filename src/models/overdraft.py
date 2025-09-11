"""Overdraft Class"""

from __future__ import annotations

from dataclasses import dataclass

from dune_client.types import Address

from src.abis.load import overdraftsmanager
from src.models.accounting_period import AccountingPeriod

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
    contract_address: str = "0x3feF04803F5F86CB750DDa8283846B48644D0C8a"

    @property
    def eth(self) -> float:
        """Returns amount in units"""
        return self.wei / 10**18

    def is_overdraft():
        return True

    def as_multisend_tx(self) -> MultiSendTx:
        """Converts Transfer into encoded MultiSendTx bytes"""
        return MultiSendTx(
            operation=MultiSendOperation.CALL,
            to=Web3.to_checksum_address(contract_address),
            value=0,
            data=OVERDRAFTSMANAGER.encodeABI(
                fn_name="addOverdraft", args=[self.account, self.wei]
            ),
        )

    def __str__(self) -> str:
        return (
            f"Overdraft(solver={self.account} ({self.name}),"
            f"period={self.period},owed={self.eth} native token units)"
        )
