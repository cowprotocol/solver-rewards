import unittest

from duneapi.types import Address
from eth_typing import URI
from gnosis.eth import EthereumClient

from src.constants import COW_TOKEN_ADDRESS, INFURA_KEY
from src.fetch.transfer_file import Transfer
from src.models.token import Token
from src.multisend import build_encoded_multisend


class TestMultiSend(unittest.TestCase):
    def setUp(self) -> None:
        node_url = f"https://goerli.infura.io/v3/{INFURA_KEY}"
        self.client = EthereumClient(URI(node_url))

    def test_multisend_encoding(self):
        receiver = Address("0xde786877a10dbb7eba25a4da65aecf47654f08ab")
        cow_token = Token(COW_TOKEN_ADDRESS)
        self.assertEqual(
            build_encoded_multisend([], client=self.client),
            "0x8d80ff0a"  # MethodID
            "0000000000000000000000000000000000000000000000000000000000000020"
            "0000000000000000000000000000000000000000000000000000000000000000"
            "0000000000000000000000000000000000000000000000000000000000000000",
        )

        native_transfer = Transfer(
            token=None, receiver=receiver, amount_wei=16
        ).as_multisend_tx()
        self.assertEqual(
            build_encoded_multisend([native_transfer], client=self.client),
            "0x8d80ff0a"  # MethodID
            "0000000000000000000000000000000000000000000000000000000000000020"
            "0000000000000000000000000000000000000000000000000000000000000055"
            "00de786877a10dbb7eba25a4da65aecf47654f08ab0000000000000000000000"
            "0000000000000000000000000000000000000000100000000000000000000000"
            "0000000000000000000000000000000000000000000000000000000000000000",
        )
        erc20_transfer = Transfer(
            token=cow_token,
            receiver=receiver,
            amount_wei=15,
        ).as_multisend_tx()
        self.assertEqual(
            build_encoded_multisend([erc20_transfer], client=self.client),
            "0x8d80ff0a"  # MethodID
            "0000000000000000000000000000000000000000000000000000000000000020"
            "0000000000000000000000000000000000000000000000000000000000000099"
            "00def1ca1fb7fbcdc777520aa7f396b4e015f497ab0000000000000000000000"
            "0000000000000000000000000000000000000000000000000000000000000000"
            "000000000000000000000000000000000000000044a9059cbb00000000000000"
            "0000000000de786877a10dbb7eba25a4da65aecf47654f08ab00000000000000"
            "0000000000000000000000000000000000000000000000000f00000000000000",
        )
        self.assertEqual(
            build_encoded_multisend(
                [erc20_transfer, native_transfer], client=self.client
            ),
            "0x8d80ff0a"  # MethodID
            "0000000000000000000000000000000000000000000000000000000000000020"
            "00000000000000000000000000000000000000000000000000000000000000ee"
            "00def1ca1fb7fbcdc777520aa7f396b4e015f497ab0000000000000000000000"
            "0000000000000000000000000000000000000000000000000000000000000000"
            "000000000000000000000000000000000000000044a9059cbb00000000000000"
            "0000000000de786877a10dbb7eba25a4da65aecf47654f08ab00000000000000"
            "0000000000000000000000000000000000000000000000000f00de786877a10d"
            "bb7eba25a4da65aecf47654f08ab000000000000000000000000000000000000"
            "0000000000000000000000000010000000000000000000000000000000000000"
            "0000000000000000000000000000000000000000000000000000000000000000",
        )
        print(
            build_encoded_multisend(
                [native_transfer, erc20_transfer], client=self.client
            ),
        )
        self.assertEqual(
            build_encoded_multisend(
                [native_transfer, erc20_transfer], client=self.client
            ),
            "0x8d80ff0a"  # MethodID
            "0000000000000000000000000000000000000000000000000000000000000020"
            "00000000000000000000000000000000000000000000000000000000000000ee"
            "00de786877a10dbb7eba25a4da65aecf47654f08ab0000000000000000000000"
            "0000000000000000000000000000000000000000100000000000000000000000"
            "00000000000000000000000000000000000000000000def1ca1fb7fbcdc77752"
            "0aa7f396b4e015f497ab00000000000000000000000000000000000000000000"
            "0000000000000000000000000000000000000000000000000000000000000000"
            "00000000000000000044a9059cbb000000000000000000000000de786877a10d"
            "bb7eba25a4da65aecf47654f08ab000000000000000000000000000000000000"
            "000000000000000000000000000f000000000000000000000000000000000000",
        )


if __name__ == "__main__":
    unittest.main()
