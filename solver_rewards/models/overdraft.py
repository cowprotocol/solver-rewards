"""Overdraft Class"""

from __future__ import annotations

from dataclasses import dataclass

from dune_client.types import Address

from solver_rewards.models.accounting_period import AccountingPeriod


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

    def __str__(self) -> str:
        return (
            f"Overdraft(solver={self.account} ({self.name}),"
            f"period={self.period},owed={self.eth} ETH)"
        )
