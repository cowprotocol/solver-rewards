"""Overdraft Class"""

from __future__ import annotations

from dataclasses import dataclass

from dune_client.types import Address
from safe_eth.safe.multi_send import MultiSendOperation, MultiSendTx
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

    @property
    def eth(self) -> float:
        """Returns amount in units"""
        return self.wei / 10**18

    def as_multisend_tx(self) -> MultiSendTx:
        """Converts Overdraft into encoded MultiSendTx bytes"""
        return MultiSendTx(
            operation=MultiSendOperation.CALL,
            to=Address("0x2BB7c386D36F5080D17eD08AB8Ea8B2899cE81C5"),
            value=0,
            data=overdraftsmanager.encodeABI(
                fn_name="addOverdraft", args=[self.account, self.wei]
            ),
        )

    def __str__(self) -> str:
        return (
            f"Overdraft(solver={self.account} ({self.name}),"
            f"period={self.period},owed={self.eth} native token units)"
        )
