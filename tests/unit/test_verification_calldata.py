"""Tests for src/verification/calldata.py."""

import unittest

from dune_client.types import Address
from eth_utils.crypto import keccak
from safe_eth.safe.multi_send import MultiSendOperation, MultiSendTx
from web3 import Web3

from src.abis.load import weth9
from src.models.token import Token
from src.models.transfer import Transfer
from src.verification.calldata import (
    ERC20_TRANSFER_SELECTOR,
    MULTI_SEND_SELECTOR,
    UNSUPPORTED_SELECTORS,
    WITHDRAW_SELECTOR,
    CalldataError,
    Erc20Transfer,
    InnerTransaction,
    NativeTransfer,
    WrappedNativeWithdrawal,
    classify,
    decode_multisend,
    decode_payout_calls,
    parse_address,
    parse_uint,
)
from tests.unit.safe_transaction_fixtures import (
    ALL_FIXTURES,
    ARBITRUM_NATIVE,
    ARBITRUM_OVERDRAFTS,
    LINEA_EMPTY,
    LINEA_NATIVE,
    MAINNET_COW,
    PLANNABLE_FIXTURES,
    load,
    multisend_txs,
    planned_calls,
    producer_encoding,
)

COW = Web3.to_checksum_address("0xdef1ca1fb7fbcdc777520aa7f396b4e015f497ab")
WETH_ARBITRUM = Web3.to_checksum_address("0x82af49447d8a07e3bd95bd0d56f35241523fbab1")
RECIPIENT = Web3.to_checksum_address("0xde786877a10dbb7eba25a4da65aecf47654f08ab")
OTHER = Web3.to_checksum_address("0x" + "ba5e" * 10)


def word(value: int) -> bytes:
    return value.to_bytes(32, "big")


def packed(operation: int, to: str, value: int, data: bytes) -> bytes:
    """One MultiSend entry, packed like MultiSendTx.encoded_data."""
    return (
        bytes([operation])
        + bytes.fromhex(to[2:])
        + word(value)
        + word(len(data))
        + data
    )


def multisend(payload: bytes) -> bytes:
    """Canonical multiSend(bytes) calldata."""
    return (
        MULTI_SEND_SELECTOR
        + word(32)
        + word(len(payload))
        + payload
        + bytes(-len(payload) % 32)
    )


def transfer_data(recipient: str, amount: int) -> bytes:
    return (
        ERC20_TRANSFER_SELECTOR
        + bytes(12)
        + bytes.fromhex(recipient[2:])
        + word(amount)
    )


def calls_from_safe_decoding(name: str) -> list:
    """The payout calls of a fixture according to Safe's own decoder."""
    result = []
    for call in planned_calls(load(name)):
        token = call.get("token")
        amount = int(call["amountAtoms"])
        if call["callType"] == "nativeTransfer":
            result.append(
                NativeTransfer(Web3.to_checksum_address(call["recipient"]), amount)
            )
        elif call["callType"] == "erc20Transfer":
            result.append(
                Erc20Transfer(
                    Web3.to_checksum_address(token),
                    Web3.to_checksum_address(call["recipient"]),
                    amount,
                )
            )
        else:
            result.append(
                WrappedNativeWithdrawal(Web3.to_checksum_address(token), amount)
            )
    return result


class TestSelectors(unittest.TestCase):
    def test_selectors_are_the_function_signatures(self):
        self.assertEqual(MULTI_SEND_SELECTOR, keccak(text="multiSend(bytes)")[:4])
        self.assertEqual(
            ERC20_TRANSFER_SELECTOR, keccak(text="transfer(address,uint256)")[:4]
        )
        self.assertEqual(WITHDRAW_SELECTOR, keccak(text="withdraw(uint256)")[:4])
        for selector, signature in UNSUPPORTED_SELECTORS.items():
            self.assertEqual(selector, keccak(text=signature)[:4])


class TestRecordedTransactions(unittest.TestCase):
    """Real payout transactions decode completely and exactly."""

    def test_fixture_boundary_reencodes_to_the_recorded_calldata(self):
        """The MultiSendTx list rebuilt from Safe's decoding, encoded like the
        payout script encodes it, is byte for byte the transaction's data."""
        for name in ALL_FIXTURES:
            recorded = load(name)
            if recorded.transaction.operation != 1:
                continue
            with self.subTest(name):
                self.assertEqual(
                    producer_encoding(multisend_txs(recorded)),
                    recorded.transaction.data,
                )

    def test_raw_entries_match_safe_decoding(self):
        for name in [MAINNET_COW, ARBITRUM_NATIVE, ARBITRUM_OVERDRAFTS, LINEA_NATIVE]:
            recorded = load(name)
            with self.subTest(name):
                self.assertEqual(
                    decode_multisend(recorded.transaction.data),
                    [
                        InnerTransaction(
                            operation=entry["operation"],
                            to=Web3.to_checksum_address(entry["to"]),
                            value=int(entry["value"]),
                            data=bytes.fromhex((entry["data"] or "0x")[2:]),
                        )
                        for entry in recorded.inner
                    ],
                )

    def test_every_call_matches_safe_decoding(self):
        for name in PLANNABLE_FIXTURES:
            recorded = load(name)
            if recorded.transaction.operation != 1:
                continue
            with self.subTest(name):
                self.assertEqual(
                    decode_payout_calls(recorded.transaction.data),
                    calls_from_safe_decoding(name),
                )

    def test_mainnet_cow_payout(self):
        calls = decode_payout_calls(load(MAINNET_COW).transaction.data)
        self.assertEqual(len(calls), 31)
        self.assertTrue(all(isinstance(call, Erc20Transfer) for call in calls))
        self.assertEqual({call.token for call in calls}, {COW})
        self.assertEqual(sum(call.amount for call in calls), 12081043070982411514571)

    def test_arbitrum_native_payout(self):
        calls = decode_payout_calls(load(ARBITRUM_NATIVE).transaction.data)
        self.assertEqual(len(calls), 24)
        self.assertEqual(
            calls[0], WrappedNativeWithdrawal(WETH_ARBITRUM, 6435645361627000999)
        )
        self.assertTrue(all(isinstance(call, NativeTransfer) for call in calls[1:]))
        self.assertEqual(sum(call.amount for call in calls[1:]), 6754301714459485126)

    def test_linea_native_payout_without_unwrap(self):
        calls = decode_payout_calls(load(LINEA_NATIVE).transaction.data)
        self.assertEqual(len(calls), 7)
        self.assertTrue(all(isinstance(call, NativeTransfer) for call in calls))

    def test_overdrafts_are_refused_not_skipped(self):
        with self.assertRaisesRegex(CalldataError, r"addOverdraft\(address,uint256\)"):
            decode_payout_calls(load(ARBITRUM_OVERDRAFTS).transaction.data)

    def test_empty_transaction_is_not_a_multisend(self):
        with self.assertRaisesRegex(CalldataError, "not a multiSend call"):
            decode_payout_calls(load(LINEA_EMPTY).transaction.data)


class TestProducerRoundTrip(unittest.TestCase):
    """Whatever the payout script encodes decodes to the same payouts."""

    def test_transfers_and_unwrap(self):
        weth = Token(WETH_ARBITRUM, 18)
        transfers = [
            Transfer(token=None, recipient=Address(RECIPIENT), amount_wei=16),
            Transfer(token=Token(COW, 18), recipient=Address(RECIPIENT), amount_wei=15),
            # partners in partners_with_wrapped_native_transfers (#634)
            Transfer(token=weth, recipient=Address(OTHER), amount_wei=14),
        ]
        unwrap = MultiSendTx(
            operation=MultiSendOperation.CALL,
            to=WETH_ARBITRUM,
            value=0,
            data=weth9().encode_abi(abi_element_identifier="withdraw", args=[13]),
        )
        transactions = [unwrap] + [t.as_multisend_tx() for t in transfers]
        self.assertEqual(
            decode_payout_calls(producer_encoding(transactions)),
            [
                WrappedNativeWithdrawal(WETH_ARBITRUM, 13),
                NativeTransfer(RECIPIENT, 16),
                Erc20Transfer(COW, RECIPIENT, 15),
                Erc20Transfer(WETH_ARBITRUM, OTHER, 14),
            ],
        )


class TestMultiSendEncodingIsStrict(unittest.TestCase):
    def setUp(self):
        self.entry = packed(0, RECIPIENT, 16, b"")
        self.valid = multisend(self.entry)

    def assert_rejected(self, data: bytes, message: str) -> None:
        with self.assertRaisesRegex(CalldataError, message):
            decode_multisend(data)

    def test_valid(self):
        self.assertEqual(
            decode_multisend(self.valid), [InnerTransaction(0, RECIPIENT, 16, b"")]
        )

    def test_wrong_selector(self):
        self.assert_rejected(b"\xde\xad\xbe\xef" + self.valid[4:], "not a multiSend")

    def test_non_canonical_offset(self):
        self.assert_rejected(
            MULTI_SEND_SELECTOR + word(64) + word(0) + self.valid[36:],
            "non-canonical offset 64",
        )

    def test_trailing_bytes_after_the_argument(self):
        for extra in (1, 31, 32, 40):
            with self.subTest(extra=extra):
                self.assert_rejected(self.valid + bytes(extra), "trailing bytes")

    def test_non_zero_abi_padding(self):
        self.assert_rejected(self.valid[:-1] + b"\x01", "non-zero padding")

    def test_truncated(self):
        for cut in (1, 11, 32, len(self.valid) - 4 - 32):
            with self.subTest(cut=cut):
                with self.assertRaises(CalldataError):
                    decode_multisend(self.valid[:-cut])

    def test_declared_length_exceeds_payload(self):
        data = MULTI_SEND_SELECTOR + word(32) + word(10**6) + self.valid[68:]
        self.assert_rejected(data, "declares 1000000 bytes")

    def test_no_transactions(self):
        self.assert_rejected(multisend(b""), "no transactions")

    def test_trailing_junk_inside_the_payload(self):
        for junk in (7, 31, 32, 84):
            with self.subTest(junk=junk):
                self.assert_rejected(
                    multisend(self.entry + b"\xff" * junk), "truncated header"
                )

    def test_inner_data_length_overrun(self):
        entry = packed(0, COW, 0, transfer_data(RECIPIENT, 1))
        overrun = entry[:53] + word(69) + entry[85:]
        self.assert_rejected(multisend(overrun), "declares 69 data bytes")


class TestInnerCallsAreStrict(unittest.TestCase):
    def assert_rejected(self, entry: InnerTransaction, message: str) -> None:
        with self.assertRaisesRegex(CalldataError, message):
            classify(3, entry)

    def test_native_transfer(self):
        self.assertEqual(
            classify(0, InnerTransaction(0, RECIPIENT, 5, b"")),
            NativeTransfer(RECIPIENT, 5),
        )

    def test_operations_other_than_call(self):
        for operation in (1, 2, 255):
            with self.subTest(operation=operation):
                self.assert_rejected(
                    InnerTransaction(operation, RECIPIENT, 5, b""),
                    f"operation {operation} is not CALL",
                )

    def test_zero_value_call_without_data(self):
        self.assert_rejected(InnerTransaction(0, RECIPIENT, 0, b""), "zero-value")

    def test_calldata_shorter_than_a_selector(self):
        self.assert_rejected(InnerTransaction(0, COW, 0, b"\xa9\x05"), "no selector")

    def test_erc20_transfer_size(self):
        data = transfer_data(RECIPIENT, 7)
        for bad in (data[:-1], data + b"\x00"):
            with self.subTest(size=len(bad)):
                self.assert_rejected(
                    InnerTransaction(0, COW, 0, bad), "must be 68 bytes"
                )

    def test_erc20_transfer_with_native_value(self):
        self.assert_rejected(
            InnerTransaction(0, COW, 1, transfer_data(RECIPIENT, 7)),
            "carries native value 1",
        )

    def test_erc20_transfer_dirty_address_padding(self):
        data = transfer_data(RECIPIENT, 7)
        dirty = data[:4] + b"\x01" + data[5:]
        self.assert_rejected(InnerTransaction(0, COW, 0, dirty), "dirty address")

    def test_zero_amounts(self):
        withdraw = WITHDRAW_SELECTOR + word(0)
        for data in (transfer_data(RECIPIENT, 0), withdraw):
            with self.subTest(selector=data[:4].hex()):
                self.assert_rejected(InnerTransaction(0, COW, 0, data), "zero amount")

    def test_withdrawal(self):
        self.assertEqual(
            classify(
                0, InnerTransaction(0, WETH_ARBITRUM, 0, WITHDRAW_SELECTOR + word(9))
            ),
            WrappedNativeWithdrawal(WETH_ARBITRUM, 9),
        )

    def test_malformed_withdrawal(self):
        data = WITHDRAW_SELECTOR + word(9)
        for bad in (data[:-1], data + b"\x00"):
            with self.subTest(size=len(bad)):
                self.assert_rejected(
                    InnerTransaction(0, WETH_ARBITRUM, 0, bad), "must be 36 bytes"
                )
        self.assert_rejected(
            InnerTransaction(0, WETH_ARBITRUM, 1, data), "carries native value"
        )

    def test_unknown_selectors(self):
        approve = keccak(text="approve(address,uint256)")[:4] + bytes(64)
        deposit = keccak(text="deposit()")[:4]
        for data in (approve, deposit):
            with self.subTest(selector=data[:4].hex()):
                self.assert_rejected(
                    InnerTransaction(0, COW, 0, data),
                    f"unsupported function selector 0x{data[:4].hex()}",
                )


class TestParseAddress(unittest.TestCase):
    def test_eip55_test_vectors(self):
        for address in (
            "0x52908400098527886E0F7030069857D2E4169EE7",
            "0x8617E340B3D01FA5F11F306F4090FD50E238070D",
            "0xde709f2102306220921060314715629080e2fb77",
            "0x27b1fdb04752bbc536007a920d24acb045561c26",
            "0x5aAeb6053F3E94C9b9A09f33669435E7Ef1BeAed",
            "0xfB6916095ca1df60bB79Ce92cE3Ea74c37c5d359",
            "0xdbF03B407c01E7cD3CBea99509d93f8DDDC8C6FB",
            "0xD1220A0cf47c7B9Be7A2E6BA89F429762e7b9aDb",
        ):
            with self.subTest(address):
                self.assertEqual(parse_address(address, "a"), address)

    def test_lowercase_is_checksummed(self):
        self.assertEqual(parse_address(COW.lower(), "a"), COW)

    def test_rejected(self):
        for value in (
            "0x5aAeb6053F3E94C9b9A09f33669435E7Ef1BeAeD",  # checksum typo
            "0x5AAEB6053F3E94C9B9A09F33669435E7EF1BEAED",  # all caps, not checksum
            COW[:-1],
            COW + "0",
            COW[2:],
            " " + COW,
            None,
            int(COW, 16),
        ):
            with self.subTest(value):
                with self.assertRaises(ValueError):
                    parse_address(value, "a")


class TestParseUint(unittest.TestCase):
    def test_accepted(self):
        for value, expected in (
            (0, 0),
            ("0", 0),
            ("123", 123),
            (2**256 - 1, 2**256 - 1),
            (str(2**256 - 1), 2**256 - 1),
        ):
            with self.subTest(value):
                self.assertEqual(parse_uint(value, "n"), expected)

    def test_rejected(self):
        for value in (
            "0012",
            "+5",
            " 12",
            "12 ",
            "1_000",
            "١٢٣",  # Arabic-Indic digits, accepted by int()
            "1e3",
            "12.0",
            "0x10",
            "",
            True,
            1.0,
            -1,
            2**256,
            str(2**256),
            None,
        ):
            with self.subTest(value):
                with self.assertRaises(ValueError):
                    parse_uint(value, "n")


if __name__ == "__main__":
    unittest.main()
