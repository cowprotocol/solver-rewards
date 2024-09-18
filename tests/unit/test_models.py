import unittest

import pandas as pd
from dune_client.types import Address
from eth_typing import HexStr
from gnosis.safe.multi_send import MultiSendTx, MultiSendOperation
from web3 import Web3

from src.abis.load import erc20
from src.constants import COW_TOKEN_ADDRESS
from src.fetch.transfer_file import Transfer
from src.models.accounting_period import AccountingPeriod
from src.models.token import Token
from src.utils.print_store import PrintStore

from tests.queries.test_internal_trades import TransferType
from tests.unit.util_methods import redirected_transfer

ONE_ETH = 10**18


class TestTransferType(unittest.TestCase):
    def setUp(self) -> None:
        self.in_user_upper = "IN_USER"
        self.in_amm_lower = "in_amm"
        self.out_user_mixed = "Out_User"
        self.invalid_type = "invalid"

    def test_valid(self):
        self.assertEqual(
            TransferType.from_str(self.in_user_upper), TransferType.IN_USER
        )
        self.assertEqual(TransferType.from_str(self.in_amm_lower), TransferType.IN_AMM)
        self.assertEqual(
            TransferType.from_str(self.out_user_mixed), TransferType.OUT_USER
        )

    def test_invalid(self):
        with self.assertRaises(ValueError) as err:
            TransferType.from_str(self.invalid_type)
        self.assertEqual(str(err.exception), f"No TransferType {self.invalid_type}!")


class TestTransfer(unittest.TestCase):
    def setUp(self) -> None:
        self.token_1 = Token(Address.from_int(1), 18)
        self.token_2 = Token(Address.from_int(2), 18)

    def test_basic_consolidation(self):
        recipients = [
            Address.from_int(0),
            Address.from_int(1),
        ]
        tokens = [
            Token(Address.from_int(2), 18),
            Token(Address.from_int(3), 18),
        ]
        transfer_list = [
            Transfer(
                token=tokens[0],
                recipient=recipients[0],
                amount_wei=1 * ONE_ETH,
            ),
            Transfer(
                token=tokens[0],
                recipient=recipients[0],
                amount_wei=2 * ONE_ETH,
            ),
            Transfer(
                token=tokens[1],
                recipient=recipients[0],
                amount_wei=3 * ONE_ETH,
            ),
            Transfer(
                token=tokens[0],
                recipient=recipients[1],
                amount_wei=4 * ONE_ETH,
            ),
            Transfer(
                token=None,
                recipient=recipients[0],
                amount_wei=5 * ONE_ETH,
            ),
            Transfer(
                token=None,
                recipient=recipients[0],
                amount_wei=6 * ONE_ETH,
            ),
            Transfer(
                token=None,
                recipient=recipients[1],
                amount_wei=7 * ONE_ETH,
            ),
            Transfer(
                token=None,
                recipient=recipients[1],
                amount_wei=8 * ONE_ETH,
            ),
        ]

        expected = [
            Transfer(
                token=None,
                recipient=recipients[1],
                amount_wei=15 * ONE_ETH,
            ),
            Transfer(
                token=None,
                recipient=recipients[0],
                amount_wei=11 * ONE_ETH,
            ),
            Transfer(
                token=tokens[0],
                recipient=recipients[1],
                amount_wei=4 * ONE_ETH,
            ),
            Transfer(
                token=tokens[0],
                recipient=recipients[0],
                amount_wei=3 * ONE_ETH,
            ),
            Transfer(
                token=tokens[1],
                recipient=recipients[0],
                amount_wei=3 * ONE_ETH,
            ),
        ]
        self.assertEqual(expected, Transfer.consolidate(transfer_list))

    def test_consolidation_with_redirect(self):
        receiver = Address.from_int(0)
        redirect = Address.from_int(1)

        transfer_list = [
            Transfer(
                token=None,
                recipient=receiver,
                amount_wei=1 * ONE_ETH,
            ),
            Transfer(
                token=None,
                recipient=receiver,
                amount_wei=2 * ONE_ETH,
            ),
            redirected_transfer(
                token=None,
                recipient=receiver,
                amount_wei=3 * ONE_ETH,
                redirect=redirect,
            ),
        ]

        expected = [
            Transfer(
                token=None,
                recipient=receiver,
                amount_wei=3 * ONE_ETH,
            ),
            redirected_transfer(
                token=None,
                recipient=receiver,
                amount_wei=3 * ONE_ETH,
                redirect=redirect,
            ),
        ]
        results = Transfer.consolidate(transfer_list)
        self.assertEqual(expected, results)

        transfer_list = [
            Transfer(
                token=None,
                recipient=receiver,
                amount_wei=1 * ONE_ETH,
            ),
            redirected_transfer(
                token=None,
                recipient=receiver,
                amount_wei=2 * ONE_ETH,
                redirect=redirect,
            ),
            redirected_transfer(
                token=None,
                recipient=receiver,
                amount_wei=3 * ONE_ETH,
                redirect=redirect,
            ),
        ]
        expected = [
            Transfer(
                token=None,
                recipient=redirect,
                amount_wei=5 * ONE_ETH,
            ),
            Transfer(
                token=None,
                recipient=receiver,
                amount_wei=1 * ONE_ETH,
            ),
        ]
        results = Transfer.consolidate(transfer_list)
        self.assertEqual(expected, results)

    def test_basic_merge_without_redirects(self):
        receiver = Address.zero()
        # Native Transfer Merge
        native_transfer1 = Transfer(
            token=None,
            recipient=receiver,
            amount_wei=ONE_ETH,
        )
        native_transfer2 = Transfer(
            token=None,
            recipient=receiver,
            amount_wei=ONE_ETH,
        )
        self.assertEqual(
            native_transfer1.merge(native_transfer2),
            Transfer(
                token=None,
                recipient=receiver,
                amount_wei=2 * ONE_ETH,
            ),
        )
        # ERC20 Transfer Merge
        erc20_transfer1 = Transfer(
            token=self.token_1,
            recipient=receiver,
            amount_wei=ONE_ETH,
        )
        erc20_transfer2 = Transfer(
            token=self.token_1,
            recipient=receiver,
            amount_wei=ONE_ETH,
        )
        self.assertEqual(
            erc20_transfer1.merge(erc20_transfer2),
            Transfer(
                token=self.token_1,
                recipient=receiver,
                amount_wei=2 * ONE_ETH,
            ),
        )

        with self.assertRaises(ValueError) as err:
            native_transfer1.merge(erc20_transfer1)
        self.assertEqual(
            f"Can't merge transfers {native_transfer1}, {erc20_transfer1}. "
            f"Requirements met [True, False]",
            str(err.exception),
        )

        with self.assertRaises(ValueError) as err:
            # Different recipients
            t1 = Transfer(
                token=self.token_1,
                recipient=Address.from_int(1),
                amount_wei=2 * ONE_ETH,
            )
            t2 = Transfer(
                token=self.token_1,
                recipient=Address.from_int(2),
                amount_wei=2 * ONE_ETH,
            )
            t1.merge(t2)
        self.assertEqual(
            f"Can't merge transfers {t1}, {t2}. Requirements met [False, True]",
            str(err.exception),
        )

        with self.assertRaises(ValueError) as err:
            # Different Token Addresses
            t1 = Transfer(
                token=self.token_1,
                recipient=receiver,
                amount_wei=2 * ONE_ETH,
            )
            t2 = Transfer(
                token=self.token_2,
                recipient=receiver,
                amount_wei=2 * ONE_ETH,
            )
            t1.merge(t2)
        self.assertEqual(
            f"Can't merge transfers {t1}, {t2}. Requirements met [True, False]",
            str(err.exception),
        )

    def test_merge_with_redirects(self):
        receiver_1 = Address.from_int(1)
        receiver_2 = Address.from_int(2)
        redirect = Address.from_int(3)

        transfer = redirected_transfer(
            token=None, recipient=receiver_1, amount_wei=ONE_ETH, redirect=redirect
        )
        expected = Transfer(
            token=None,
            recipient=redirect,
            amount_wei=2 * ONE_ETH,
        )
        self.assertEqual(
            transfer.merge(
                redirected_transfer(
                    token=None,
                    recipient=receiver_2,
                    amount_wei=ONE_ETH,
                    redirect=redirect,
                )
            ),
            # Both redirected to same address get merged.
            expected,
        )
        self.assertEqual(
            transfer.merge(
                Transfer(
                    token=None,
                    recipient=redirect,
                    amount_wei=ONE_ETH,
                )
            ),
            # one redirected and the other with initial recipient as redirect address get merged.
            expected,
        )

        with self.assertRaises(ValueError) as err:
            # Fail to merge redirected transfer with one whose recipient
            # is the original receiver of the redirected transfer
            other = Transfer(
                token=None,
                recipient=receiver_1,
                amount_wei=ONE_ETH,
            )
            transfer.merge(other)
        self.assertEqual(
            f"Can't merge transfers {transfer}, {other}. Requirements met [False, True]",
            str(err.exception),
        )

    def test_from_dict(self):
        receiver = Address.from_int(1)
        self.assertEqual(
            Transfer.from_dict(
                {
                    "token_address": None,
                    "receiver": receiver.address,
                    "amount": "1234000000000000000",
                }
            ),
            Transfer(
                token=None,
                recipient=receiver,
                amount_wei=1234 * 10**15,
            ),
        )

        self.assertEqual(
            Transfer.from_dict(
                {
                    "token_address": COW_TOKEN_ADDRESS.address,
                    "receiver": Address.from_int(1).address,
                    "amount": "1234000000000000000",
                }
            ),
            Transfer(
                token=Token(COW_TOKEN_ADDRESS),
                recipient=Address.from_int(1),
                amount_wei=1234 * 10**15,
            ),
        )

    def test_from_dataframe(self):
        receiver = Address.from_int(1)
        token_address = COW_TOKEN_ADDRESS.address
        transfer_df = pd.DataFrame(
            {
                "token_address": [None, token_address],
                "receiver": [str(receiver.address), str(receiver.address)],
                "amount": ["12345", "678910"],
                "other_useless_column": [True, False],
            }
        )
        expected = [
            Transfer(
                token=None,
                recipient=receiver,
                amount_wei=12345,
            ),
            Transfer(
                token=Token(COW_TOKEN_ADDRESS),
                recipient=receiver,
                amount_wei=678910,
            ),
        ]

        self.assertEqual(expected, Transfer.from_dataframe(transfer_df))

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
            token=Token(COW_TOKEN_ADDRESS),
            recipient=Address(receiver),
            amount_wei=15,
        )
        self.assertEqual(
            erc20_transfer.as_multisend_tx(),
            MultiSendTx(
                operation=MultiSendOperation.CALL,
                to=COW_TOKEN_ADDRESS.address,
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
                    token=Token(COW_TOKEN_ADDRESS),
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
