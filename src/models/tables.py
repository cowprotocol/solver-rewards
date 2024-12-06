"""Data structure containing the supported sync tables"""
from enum import Enum


class SyncTable(Enum):
    """Enum for Deployment Supported Table Sync"""

    ORDER_REWARDS = "order_rewards"
    BATCH_REWARDS = "batch_rewards"
    BATCH_DATA = "batch_data"

    def __str__(self) -> str:
        return str(self.value)

    @staticmethod
    def supported_tables() -> list[str]:
        """Returns a list of supported tables (i.e. valid object contructors)."""
        return [str(t) for t in list(SyncTable)]
