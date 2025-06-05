"""Data structure containing the supported sync tables"""

from enum import Enum


class SyncTable(Enum):
    """Enum for Deployment Supported Table Sync"""

    BATCH_DATA = "batch_data"
    ORDER_DATA = "order_data"

    def __str__(self) -> str:
        return str(self.value)

    @staticmethod
    def supported_tables() -> list[str]:
        """Returns a list of supported tables (i.e. valid object constructors)."""
        return [str(t) for t in list(SyncTable)]
