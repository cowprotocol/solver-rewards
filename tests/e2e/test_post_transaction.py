import os
import unittest

from duneapi.types import Address
from eth_typing import URI
from gnosis.eth import EthereumNetwork, EthereumClient

from src.constants import w3
from src.fetch.transfer_file import Transfer
from src.models import Token
from src.multisend import post_multisend


class TestTransactionPost(unittest.TestCase):
    def setUp(self) -> None:
        # PK for deterministic ganache default account `ganache-cli -d`
        self.pk = "0x4f3edf983ac636a65a842ce7c78d9aa706d3b113bce9c46f30d7d21715b23b1d"
        self.test_safe = "0x8990c564ec303C7b26d3d5556ef0910E58Be08Ce"
        self.owl = Token("0xa7D1C04fAF998F9161fC9F800a99A809b84cfc9D", 18)
        self.receiver = Address("0xFFcf8FDEE72ac11b5c542428B35EEF5769C409f0")
        self.client = EthereumClient(
            URI(f"https://rinkeby.infura.io/v3/{os.environ.get('INFURA_KEY')}")
        )

    def test_token_decimals(self):
        token_transfer = Transfer(
            token=self.owl,
            amount_wei=15,
            receiver=self.receiver,
        )
        native_transfer = Transfer(token=None, receiver=self.receiver, amount_wei=2)

        post_multisend(
            safe_address=w3.toChecksumAddress(self.test_safe),
            network=EthereumNetwork.RINKEBY,
            transfers=[
                token_transfer.as_multisend_tx(),
                native_transfer.as_multisend_tx(),
            ],
            client=self.client,
            signing_key=self.pk,
        )


if __name__ == "__main__":
    unittest.main()
