"""
Simple wrapper for print statements that saves all the messages chronologically in a list
"""


class PrintStore:
    """Prints and saves messages in a list"""

    def __init__(self) -> None:
        self.store: list[str] = []

    def print(self, message: str) -> None:
        """Add message to store and print"""
        self.store.append(message)
        print(message)

    def get_value(self) -> str:
        """Returns the print history"""
        return "\n".join(self.store)
