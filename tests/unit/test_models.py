import unittest

import pandas as pd
from dune_client.types import Address
from eth_typing import HexStr
from gnosis.safe.multi_send import MultiSendTx, MultiSendOperation
from web3 import Web3

from src.abis.load import erc20
from src.config import config
from src.fetch.transfer_file import Transfer
from src.models.accounting_period import AccountingPeriod
from src.models.token import Token

from tests.unit.util_methods import redirected_transfer

ONE_ETH = 10**18


class TestTransfer(unittest.TestCase):
    def setUp(self) -> None:
        self.token_1 = Token(Address.from_int(1), 18)
        self.token_2 = Token(Address.from_int(2), 18)

    def test_basic_as_multisend_tx(self):
        receiver = Web3.to_checksum_address(
            "0x90F8bf6A479f320ead074411a4B0e7944Ea8c9C1"
        )
        native_transfer = Transfer(
            token=None, recipient=Address(receiver), amount_wei=16
        )
        self.assertEqual(
            native_transfer.as_multisend_tx(),
            MultiSendTx(
                operation=MultiSendOperation.CALL,
                to=receiver,
                value=16,
                data=HexStr("0x"),
            ),
        )
        erc20_transfer = Transfer(
            token=Token(config.payment_config.cow_token_address),
            recipient=Address(receiver),
            amount_wei=15,
        )
        self.assertEqual(
            erc20_transfer.as_multisend_tx(),
            MultiSendTx(
                operation=MultiSendOperation.CALL,
                to=config.payment_config.cow_token_address.address,
                value=0,
                data=erc20().encodeABI(fn_name="transfer", args=[receiver, 15]),
            ),
        )

    def test_as_multisend_tx_with_redirects(self):
        receiver = Address.from_int(1)
        redirect = Address.from_int(2)
        native_transfer = redirected_transfer(
            token=None, recipient=receiver, amount_wei=16, redirect=redirect
        )
        self.assertEqual(
            native_transfer.as_multisend_tx(),
            MultiSendTx(
                operation=MultiSendOperation.CALL,
                to=redirect.address,
                value=16,
                data=HexStr("0x"),
            ),
        )
        token_address = Address.from_int(1)
        token = Token(address=token_address, decimals=10)
        erc20_transfer = redirected_transfer(
            token=token,
            recipient=receiver,
            amount_wei=15,
            redirect=redirect,
        )
        self.assertEqual(
            erc20_transfer.as_multisend_tx(),
            MultiSendTx(
                operation=MultiSendOperation.CALL,
                to=token_address.address,
                value=0,
                data=erc20().encodeABI(fn_name="transfer", args=[redirect.address, 15]),
            ),
        )

    def test_summarize(self):
        receiver = Address.from_int(1)
        eth_amount = 123456789101112131415
        cow_amount = 9999999999999999999999999
        result = Transfer.summarize(
            [
                Transfer(token=None, recipient=receiver, amount_wei=eth_amount),
                Transfer(
                    token=Token(config.payment_config.cow_token_address),
                    recipient=receiver,
                    amount_wei=cow_amount,
                ),
            ]
        )
        self.assertEqual(
            result,
            "Total ETH Funds needed: 123.4568\nTotal COW Funds needed: 10000000.0000\n",
        )


class TestAccountingPeriod(unittest.TestCase):
    def test_str(self):
        self.assertEqual(
            "2022-01-01-to-2022-01-08", str(AccountingPeriod("2022-01-01"))
        )
        self.assertEqual(
            "2022-01-01-to-2022-01-07", str(AccountingPeriod("2022-01-01", 6))
        )

    def test_hash(self):
        self.assertEqual(2022010120220108, hash(AccountingPeriod("2022-01-01")))
        self.assertEqual(2022010120220107, hash(AccountingPeriod("2022-01-01", 6)))

    def test_invalid(self):
        bad_date_string = "Invalid date string"
        with self.assertRaises(ValueError) as err:
            AccountingPeriod(bad_date_string)

        self.assertEqual(
            f"time data '{bad_date_string}' does not match format '%Y-%m-%d'",
            str(err.exception),
        )


if __name__ == "__main__":
    unittest.main()
