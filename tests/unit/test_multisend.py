import unittest

from dune_client.types import Address
from eth_typing import URI
from safe_eth.eth import EthereumClient

from src.abis.load import weth9
from src.config import Network, PaymentConfig
from src.fetch.transfer_file import Transfer
from src.models.token import Token
from src.multisend import build_encoded_multisend, prepend_unwrap_if_necessary


class TestMultiSend(unittest.TestCase):
    def setUp(self) -> None:
        node_url = "https://ethereum-rpc.publicnode.com"
        self.client = EthereumClient(URI(node_url))
        self.payment_config = PaymentConfig.from_network(Network.MAINNET)

    def test_prepend_unwrap(self):
        safe_address = self.payment_config.payment_safe_address_native
        eth_balance = self.client.get_balance(safe_address)
        weth = weth9(self.client.w3, self.payment_config.wrapped_native_token_address)

        weth_unwrap_amount = 1
        transactions = [
            Transfer(
                token=None,
                recipient=Address.zero(),
                amount_wei=eth_balance
                + weth_unwrap_amount,  # More ETH than account has!
            ).as_multisend_tx()
        ]
        transactions = prepend_unwrap_if_necessary(
            self.client,
            safe_address,
            transactions,
            self.payment_config.wrapped_native_token_address,
            skip_validation=True,
        )

        self.assertEqual(2, len(transactions))
        unwrap = transactions[0]
        self.assertEqual(weth.address, unwrap.to)

        unwrap_method_id = "0x2e1a7d4d"
        # 32-byte hex encoding of weth balance
        hex_weth_unwrap_amount = hex(weth_unwrap_amount)[2:].rjust(64, "0")
        self.assertEqual(
            f"{unwrap_method_id.lstrip('0x')}{hex_weth_unwrap_amount}",
            unwrap.data.hex().lstrip("0x"),  # normalize actual
        )

    def test_prepend_unwrap_error(self):
        many_eth = 99999999 * 10**18
        safe_address = self.payment_config.payment_safe_address_native
        big_native_transfer = Transfer(
            token=None, recipient=Address.zero(), amount_wei=many_eth
        ).as_multisend_tx()

        with self.assertRaises(ValueError):
            # Nobody has that much ETH!
            prepend_unwrap_if_necessary(
                client=self.client,
                safe_address=safe_address,
                transactions=[big_native_transfer],
                wrapped_native_token=self.payment_config.wrapped_native_token_address,
            )

    def test_multisend_encoding(self):
        receiver = Address("0xde786877a10dbb7eba25a4da65aecf47654f08ab")
        cow_token = Token(self.payment_config.cow_token_address)
        self.assertEqual(
            build_encoded_multisend([], client=self.client),
            bytes.fromhex(
                "8d80ff0a"  # MethodID
                "0000000000000000000000000000000000000000000000000000000000000020"
                "0000000000000000000000000000000000000000000000000000000000000000",
            ),
        )

        native_transfer = Transfer(
            token=None, recipient=receiver, amount_wei=16
        ).as_multisend_tx()
        self.assertEqual(
            build_encoded_multisend([native_transfer], client=self.client),
            bytes.fromhex(
                "8d80ff0a"  # MethodID
                "0000000000000000000000000000000000000000000000000000000000000020"
                "0000000000000000000000000000000000000000000000000000000000000055"
                "00de786877a10dbb7eba25a4da65aecf47654f08ab0000000000000000000000"
                "0000000000000000000000000000000000000000100000000000000000000000"
                "0000000000000000000000000000000000000000000000000000000000000000",
            ),
        )
        erc20_transfer = Transfer(
            token=cow_token,
            recipient=receiver,
            amount_wei=15,
        ).as_multisend_tx()
        self.assertEqual(
            build_encoded_multisend([erc20_transfer], client=self.client),
            bytes.fromhex(
                "8d80ff0a"  # MethodID
                "0000000000000000000000000000000000000000000000000000000000000020"
                "0000000000000000000000000000000000000000000000000000000000000099"
                "00def1ca1fb7fbcdc777520aa7f396b4e015f497ab0000000000000000000000"
                "0000000000000000000000000000000000000000000000000000000000000000"
                "000000000000000000000000000000000000000044a9059cbb00000000000000"
                "0000000000de786877a10dbb7eba25a4da65aecf47654f08ab00000000000000"
                "0000000000000000000000000000000000000000000000000f00000000000000",
            ),
        )
        self.assertEqual(
            build_encoded_multisend(
                [erc20_transfer, native_transfer], client=self.client
            ),
            bytes.fromhex(
                "8d80ff0a"  # MethodID
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
            ),
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
            bytes.fromhex(
                "8d80ff0a"  # MethodID
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
            ),
        )


if __name__ == "__main__":
    unittest.main()
