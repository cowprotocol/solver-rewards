"""
Simple wrapper for print statements that saves all the messages chronologically in a list
"""

from collections import defaultdict
from enum import Enum


class Category(Enum):
    """Known Categories for PrintStore"""

    GENERAL = "Overview"
    TOTALS = "Totals"
    OVERDRAFT = "Overdraft"
    COW_REDIRECT = "COW Redirects"
    ETH_REDIRECT = "ETH Redirects (Positive Slippage)"
    SLIPPAGE = "Negative Slippage"
    EXECUTION = "Execution Details"


class PrintStore:
    """Prints and saves messages in a list"""

    def __init__(self) -> None:
        self.store: dict[Category, list[str]] = defaultdict(list)

    def print(self, message: str, category: Category) -> None:
        """Add message to store and print"""
        self.store[category].append(message)
        print(message)

    def get_value(self, category: Category) -> str:
        """Returns the print history"""
        return "\n".join(self.store[category])

    def get_values(self) -> dict[str, str]:
        """Returns partitioned dictionary of values per category"""
        return {category.value: self.get_value(category) for category in self.store}
