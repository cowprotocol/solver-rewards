"""
Script to query and display total funds distributed for specified accounting period.
"""
from dataclasses import dataclass

from src.models.accounting_period import AccountingPeriod


@dataclass
class PeriodTotals:
    """Total amount reimbursed for accounting period"""

    period: AccountingPeriod
    execution_cost_eth: int
    cow_rewards: int
    realized_fees_eth: int
