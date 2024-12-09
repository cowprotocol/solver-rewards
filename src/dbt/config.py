"""Configuration details for sync jobs"""

from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path


@dataclass
class SyncConfig:
    """
    This data class contains all the credentials and volume paths
    required to sync with both a persistent volume and Dune's S3 Buckets.
    """

    volume_path: Path
    # File System
    sync_file: str = "sync_block.csv"
    sync_column: str = "last_synced_block"


@dataclass
class BatchDataSyncConfig:
    """Configuration for batch data sync."""

    # The name of the table to upload to
    table: str = "batch_data_test"
    # Description of the table (for creation)
    description: str = "Table containing raw batch data"


@dataclass
class OrderDataSyncConfig:
    """Configuration for order data sync."""

    # The name of the table to upload to
    table: str = "order_data_test"
    # Description of the table (for creation)
    description: str = "Table containing raw order data"
