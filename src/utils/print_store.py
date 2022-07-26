

class PrintStore:

    def __init__(self):
        self.store = []

    def print(self, message: str):
        self.store.append(message)
        print(message)

    def get_value(self) -> str:
        return "\n".join(self.store)