import unittest

from dune_client.types import Address
from eth_typing import URI
from gnosis.eth import EthereumNetwork, EthereumClient

from web3 import Web3
from src.fetch.transfer_file import Transfer
from src.models.token import Token
from src.multisend import post_multisend
import pytest


class TestTransactionPost(unittest.TestCase):
    def setUp(self) -> None:
        # PK for deterministic ganache default account `ganache-cli -d`
        self.pk = "0x4f3edf983ac636a65a842ce7c78d9aa706d3b113bce9c46f30d7d21715b23b1d"
        self.test_safe = "0xAb4178341C37e2307726361eEAE47FCA606cd458"
        self.cow = Token("0x3430d04E42a722c5Ae52C5Bffbf1F230C2677600", 18)
        self.receiver = Address("0xFFcf8FDEE72ac11b5c542428B35EEF5769C409f0")
        self.client = EthereumClient(URI("https://rpc.ankr.com/eth_goerli"))
    @pytest.mark.skip(
        reason="Need to deploy a safe owned by the pk above on sepolia"
        "Issue https://github.com/cowprotocol/solver-rewards/issues/387"
    )
    def test_post_multisend(self):
        token_transfer = Transfer(
            token=self.cow,
            amount_wei=15,
            recipient=self.receiver,
        )
        native_transfer = Transfer(token=None, recipient=self.receiver, amount_wei=2)

        post_multisend(
            safe_address=Web3().to_checksum_address(self.test_safe),
            network=EthereumNetwork.GOERLI,
            transactions=[
                token_transfer.as_multisend_tx(),
                native_transfer.as_multisend_tx(),
            ],
            client=self.client,
            signing_key=self.pk,
        )


if __name__ == "__main__":
    unittest.main()
