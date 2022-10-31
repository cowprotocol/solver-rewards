"""
Relative imports are generally bad to include in a project.
It causes problems when people are not necessarily running the scripts from the project root
These utilities eliminate the need to use relative paths.
"""
import os

from src.constants import QUERY_PATH, DASHBOARD_PATH


def query_file(filename: str) -> str:
    """Returns proper path for filename in QUERY_PATH"""
    return os.path.join(QUERY_PATH, filename)


def dashboard_file(filename: str) -> str:
    """Returns proper path for filename in DASHBOARD_PATH"""
    return os.path.join(DASHBOARD_PATH, filename)
