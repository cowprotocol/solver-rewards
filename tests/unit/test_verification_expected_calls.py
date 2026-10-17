"""Tests for src/verification/expected_calls.py."""

import unittest

from dune_client.types import Address
from eth_utils.address import is_checksum_address

from src.models.token import Token
from src.models.transfer import Transfer
from src.verification.calldata import (
    UINT256_MAX,
    Erc20Transfer,
    NativeTransfer,
    WrappedNativeWithdrawal,
    decode_payout_calls,
)
from src.verification.expected_calls import (
    cow_multisend_calls,
    expected_unwrap,
    native_multisend_calls,
    transfer_calls,
)
from tests.unit.safe_transaction_fixtures import producer_encoding

COW = "0xDEf1CA1fb7FBcDC777520aa7f396b4E015F497aB"
MAINNET_WETH = "0xC02aaA39b223FE8D0A0e5C4F27eAD9083C756Cc2"
SOLVER = "0xe8599F3cc5D38a9aD6F3684cd5CEa72f10Dbc383"
OTHER_SOLVER = "0xDe786877a10DBb7EBa25a4DA65aEcf47654F08ab"
# Recipients of the WETH transfers in the mainnet native payout at nonce 1466.
PROTOCOL_FEE_SAFE = "0x22af3D38E50ddedeb7C47f36faB321eC3Bb72A76"
PARTNER = "0x0A61B9F341a3ec8a8112D7dD6FBBC62B7FDF437e"


def native(recipient: str, amount: int) -> Transfer:
    return Transfer(token=None, recipient=Address(recipient), amount_wei=amount)


def erc20(token: str, recipient: str, amount: int) -> Transfer:
    # Token(address) without decimals would ask a node for them.
    return Transfer(
        token=Token(token, 18), recipient=Address(recipient), amount_wei=amount
    )


def native_payout() -> list[Transfer]:
    """Native token transfers as main() composes them since #642: native
    transfers to solvers and wrapped native token transfers."""
    return [
        native(SOLVER, 3 * 10**17),
        erc20(MAINNET_WETH, PROTOCOL_FEE_SAFE, 5 * 10**16),
        native(OTHER_SOLVER, 2 * 10**17),
        erc20(MAINNET_WETH, PARTNER, 10**16),
    ]


NATIVE_TOTAL = 5 * 10**17
WRAPPED_NATIVE_TOTAL = 6 * 10**16


def unwrap_for(transfers: list[Transfer], balance: int):
    return expected_unwrap(
        transfers, native_balance=balance, wrapped_native_token=MAINNET_WETH
    )


def native_calls_for(transfers: list[Transfer], balance: int):
    return native_multisend_calls(
        transfers, native_balance=balance, wrapped_native_token=MAINNET_WETH
    )


class TestTransferCalls(unittest.TestCase):
    def test_native_transfer(self):
        self.assertEqual(
            transfer_calls([native(SOLVER, 16)]), (NativeTransfer(SOLVER, 16),)
        )

    def test_cow_transfer(self):
        self.assertEqual(
            transfer_calls([erc20(COW, SOLVER, 15 * 10**18)]),
            (Erc20Transfer(COW, SOLVER, 15 * 10**18),),
        )

    def test_wrapped_native_token_transfer_is_an_erc20_transfer(self):
        self.assertEqual(
            transfer_calls([erc20(MAINNET_WETH, PARTNER, 14)]),
            (Erc20Transfer(MAINNET_WETH, PARTNER, 14),),
        )

    def test_addresses_are_checksummed(self):
        """Every spelling dune_client's Address accepts, which stores it in
        lowercase, becomes the EIP-55 checksum."""
        spellings = {
            "checksummed": lambda address: address,
            "lowercase": str.lower,
            "uppercase digits": lambda address: "0x" + address[2:].upper(),
            "unprefixed": lambda address: address[2:].lower(),
            "Dune bytea": lambda address: "\\x" + address[2:].lower(),
        }
        for label, spell in spellings.items():
            with self.subTest(label):
                calls = transfer_calls(
                    [
                        native(spell(SOLVER), 1),
                        erc20(spell(COW), spell(OTHER_SOLVER), 2),
                    ]
                )
                self.assertEqual(
                    calls,
                    (NativeTransfer(SOLVER, 1), Erc20Transfer(COW, OTHER_SOLVER, 2)),
                )
                for address in (calls[0].recipient, calls[1].token, calls[1].recipient):
                    self.assertTrue(is_checksum_address(address), address)
        self.assertNotEqual(Address(SOLVER).address, SOLVER)

    def test_order_is_preserved(self):
        transfers = native_payout() + [erc20(COW, SOLVER, 7)]
        expected = (
            NativeTransfer(SOLVER, 3 * 10**17),
            Erc20Transfer(MAINNET_WETH, PROTOCOL_FEE_SAFE, 5 * 10**16),
            NativeTransfer(OTHER_SOLVER, 2 * 10**17),
            Erc20Transfer(MAINNET_WETH, PARTNER, 10**16),
            Erc20Transfer(COW, SOLVER, 7),
        )
        self.assertEqual(transfer_calls(transfers), expected)
        self.assertEqual(transfer_calls(transfers[::-1]), expected[::-1])

    def test_identical_transfers_each_get_a_call(self):
        """Identical transfers, adjacent or not, are separate payouts: each is
        paid with its own call, in order, and every identical native amount
        counts towards the unwrap."""
        transfers = [
            native(SOLVER, 5),
            erc20(MAINNET_WETH, PARTNER, 7),
            erc20(MAINNET_WETH, PARTNER, 7),
            native(SOLVER, 5),
        ]
        calls = (
            NativeTransfer(SOLVER, 5),
            Erc20Transfer(MAINNET_WETH, PARTNER, 7),
            Erc20Transfer(MAINNET_WETH, PARTNER, 7),
            NativeTransfer(SOLVER, 5),
        )
        self.assertEqual(transfer_calls(transfers), calls)
        self.assertEqual(
            unwrap_for(transfers, 0), WrappedNativeWithdrawal(MAINNET_WETH, 10)
        )
        self.assertEqual(
            native_calls_for(transfers, 0),
            (WrappedNativeWithdrawal(MAINNET_WETH, 10), *calls),
        )
        self.assertEqual(
            cow_multisend_calls([erc20(COW, SOLVER, 9), erc20(COW, SOLVER, 9)]),
            (Erc20Transfer(COW, SOLVER, 9), Erc20Transfer(COW, SOLVER, 9)),
        )

    def test_same_calls_as_the_payout_script_encodes(self):
        """The calls equal what CoW's Transfer.as_multisend_tx encodes, as the
        strict decoder reads it back. The encoder is the test's oracle; the
        module under test never calls it."""
        transfers = native_payout() + [
            erc20(COW.lower(), OTHER_SOLVER[2:], 7),
            native("\\x" + PARTNER[2:].lower(), 9),
        ]
        encoded = producer_encoding([t.as_multisend_tx() for t in transfers])
        self.assertEqual(decode_payout_calls(encoded), list(transfer_calls(transfers)))

    def test_no_transfers(self):
        self.assertEqual(transfer_calls([]), ())
        self.assertEqual(cow_multisend_calls([]), ())
        self.assertEqual(native_calls_for([], 0), ())


class TestUnwrap(unittest.TestCase):
    """The unwrap rule of prepend_unwrap_if_necessary, which auto_propose
    applies to the native token transaction only."""

    def test_shortfall_is_unwrapped_exactly(self):
        balance = 123456789
        self.assertEqual(
            unwrap_for(native_payout(), balance),
            WrappedNativeWithdrawal(MAINNET_WETH, NATIVE_TOTAL - balance),
        )
        self.assertEqual(
            unwrap_for(native_payout(), 0),
            WrappedNativeWithdrawal(MAINNET_WETH, NATIVE_TOTAL),
        )

    def test_one_wei_shortfall(self):
        self.assertEqual(
            unwrap_for(native_payout(), NATIVE_TOTAL - 1),
            WrappedNativeWithdrawal(MAINNET_WETH, 1),
        )

    def test_equal_balance_needs_no_unwrap(self):
        self.assertIsNone(unwrap_for(native_payout(), NATIVE_TOTAL))
        self.assertEqual(
            native_calls_for(native_payout(), NATIVE_TOTAL),
            transfer_calls(native_payout()),
        )

    def test_surplus_needs_no_unwrap(self):
        for balance in (NATIVE_TOTAL + 1, 10**24, UINT256_MAX):
            with self.subTest(balance=balance):
                self.assertIsNone(unwrap_for(native_payout(), balance))
                self.assertEqual(
                    native_calls_for(native_payout(), balance),
                    transfer_calls(native_payout()),
                )

    def test_wrapped_native_transfers_are_not_counted(self):
        """Wrapped native token transfers are ERC-20 calls without native
        value, so they never add to the native token the Safe needs."""
        self.assertIsNone(unwrap_for(native_payout(), NATIVE_TOTAL))
        self.assertEqual(
            unwrap_for(native_payout(), NATIVE_TOTAL - WRAPPED_NATIVE_TOTAL),
            WrappedNativeWithdrawal(MAINNET_WETH, WRAPPED_NATIVE_TOTAL),
        )

    def test_only_wrapped_native_transfers_need_no_unwrap(self):
        transfers = [
            erc20(MAINNET_WETH, PROTOCOL_FEE_SAFE, 5 * 10**16),
            erc20(MAINNET_WETH, PARTNER, 10**16),
        ]
        self.assertIsNone(unwrap_for(transfers, 0))
        self.assertEqual(
            native_calls_for(transfers, 0),
            (
                Erc20Transfer(MAINNET_WETH, PROTOCOL_FEE_SAFE, 5 * 10**16),
                Erc20Transfer(MAINNET_WETH, PARTNER, 10**16),
            ),
        )

    def test_withdrawal_is_the_first_call(self):
        calls = native_calls_for(native_payout(), 10**17)
        self.assertEqual(
            calls,
            (
                WrappedNativeWithdrawal(MAINNET_WETH, 4 * 10**17),
                *transfer_calls(native_payout()),
            ),
        )
        self.assertEqual(
            [isinstance(call, WrappedNativeWithdrawal) for call in calls],
            [True, False, False, False, False],
        )

    def test_wrapped_native_token_is_checksummed(self):
        self.assertEqual(
            native_multisend_calls(
                [native(SOLVER, 5)],
                native_balance=2,
                wrapped_native_token=MAINNET_WETH.lower(),
            )[0],
            WrappedNativeWithdrawal(MAINNET_WETH, 3),
        )

    def test_cow_transaction_never_unwraps(self):
        """auto_propose passes wrapped_amount=None for the COW transaction, so
        whatever it pays, no withdrawal is prepended."""
        transfers = [erc20(COW, SOLVER, 10**21), *native_payout()]
        calls = cow_multisend_calls(transfers)
        self.assertEqual(calls, transfer_calls(transfers))
        self.assertFalse(
            any(isinstance(call, WrappedNativeWithdrawal) for call in calls)
        )


class TestRejectedInput(unittest.TestCase):
    """Inputs the payout script cannot build a transaction from."""

    def test_invalid_native_balance(self):
        for balance in (-1, -(10**18), True, 1.5, UINT256_MAX + 1, None):
            with self.subTest(balance=balance):
                with self.assertRaisesRegex(ValueError, "native_balance"):
                    unwrap_for(native_payout(), balance)
                with self.assertRaisesRegex(ValueError, "native_balance"):
                    native_calls_for(native_payout(), balance)

    def test_invalid_amounts(self):
        """Transfer asserts a positive amount on construction only."""
        for amount in (0, -1, True, UINT256_MAX + 1):
            with self.subTest(amount=amount):
                transfers = native_payout()
                transfers[1].amount_wei = amount
                for build in (
                    transfer_calls,
                    cow_multisend_calls,
                    lambda ts: native_calls_for(ts, NATIVE_TOTAL),
                    lambda ts: unwrap_for(ts, 0),
                ):
                    with self.assertRaisesRegex(
                        ValueError, r"transfers\[1\]\.amount_wei"
                    ):
                        build(transfers)

    def test_invalid_wrapped_native_token(self):
        for token in (
            "0xC02aaA39b223FE8D0A0e5C4F27eAD9083C756CC2",  # checksum typo
            MAINNET_WETH[2:],
            MAINNET_WETH[:-1],
            None,
        ):
            with self.subTest(token=token):
                for transfers in ([], native_payout()):
                    with self.assertRaisesRegex(ValueError, "wrapped_native_token"):
                        native_multisend_calls(
                            transfers, native_balance=0, wrapped_native_token=token
                        )

    def test_unwrap_beyond_uint256(self):
        transfers = [native(SOLVER, UINT256_MAX), native(OTHER_SOLVER, UINT256_MAX)]
        self.assertEqual(len(transfer_calls(transfers)), 2)
        with self.assertRaisesRegex(ValueError, "unwrap: .* is not a uint256"):
            unwrap_for(transfers, 0)
        self.assertEqual(
            unwrap_for(transfers, UINT256_MAX),
            WrappedNativeWithdrawal(MAINNET_WETH, UINT256_MAX),
        )


if __name__ == "__main__":
    unittest.main()
