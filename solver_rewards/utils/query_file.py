"""
Relative imports are generally bad to include in a project.
It causes problems when people are not necessarily running the scripts from the project root
These utilities eliminate the need to use relative paths.
"""

import os
import importlib

from solver_rewards.config import IOConfig

io_config = IOConfig.from_env()


def open_query(filename: str) -> str:
    """Opens `filename` and returns as string"""
    with importlib.resources.open_text('solver_rewards.sql.orderbook', filename) as file:
        return file.read()


def open_dashboard_query(filename: str) -> str:
    """Opens `filename` from DASHBOARD_PATH and returns as string"""
    with open(dashboard_file(filename), "r", encoding="utf-8") as file:
        return file.read()


def dashboard_file(filename: str) -> str:
    """Returns proper path for filename in DASHBOARD_PATH"""
    return os.path.join(io_config.dashboard_dir, filename)
