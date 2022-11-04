"""
A few project level Enums and utils
"""
import argparse
from enum import Enum

from duneapi.types import QueryParameter

from src.logger import set_log

log = set_log(__name__)


class Environment(Enum):
    """Enum for Deployment Environments"""

    STAGING = "barn"
    PRODUCTION = "prod"
    TEST = "test"

    def __str__(self) -> str:
        return str(self.value)

    def as_query_param(self) -> QueryParameter:
        """Converts Environment to Dune Query Parameter"""
        return QueryParameter.enum_type(
            "Environment", str(self), [str(e) for e in Environment]
        )


def update_args() -> argparse.Namespace:
    """Arguments used to pass table environment name"""
    parser = argparse.ArgumentParser()
    parser.add_argument(
        "-e",
        "--environment",
        type=Environment,
        choices=list(Environment),
        default=Environment.TEST,
    )
    args = parser.parse_args()
    return args
