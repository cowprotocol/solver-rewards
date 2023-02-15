"""Overdraft Class"""
from __future__ import annotations

from dataclasses import dataclass

from dune_client.types import Address

from src.models.accounting_period import AccountingPeriod
from src.models.slippage import SolverSlippage
from src.models.token import TokenType
from src.models.transfer import Transfer


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

    @classmethod
    def from_objects(
        cls, transfer: Transfer, slippage: SolverSlippage, period: AccountingPeriod
    ) -> Overdraft:
        """Constructs an overdraft instance based on Transfer & Slippage"""
        assert transfer.receiver == slippage.solver_address
        assert transfer.token_type == TokenType.NATIVE
        overdraft = transfer.amount_wei + slippage.amount_wei
        assert overdraft < 0, "This is why we are here."
        return cls(
            period=period,
            name=slippage.solver_name,
            account=slippage.solver_address,
            wei=abs(overdraft),
        )

    @property
    def eth(self) -> float:
        """Returns amount in units"""
        return self.wei / 10**18

    def __str__(self) -> str:
        return (
            f"Overdraft(solver={self.account} ({self.name}),"
            f"period={self.period},owed={self.eth} ETH)"
        )
