"""Tests for src/verification/safe_transaction.py."""

import dataclasses
import unittest

from eth_utils.crypto import keccak
from hexbytes import HexBytes
from safe_eth.safe import SafeTx
from web3 import Web3

from src.verification.calldata import CalldataError
from src.verification.safe_transaction import (
    DOMAIN_SEPARATOR_TYPEHASH,
    EXEC_TRANSACTION_SELECTOR,
    SAFE_TX_TYPEHASH,
    SafeTransaction,
    decode_exec_transaction,
)
from tests.unit.safe_transaction_fixtures import (
    ALL_FIXTURES,
    ARBITRUM_NATIVE,
    LINEA_EMPTY,
    MAINNET_COW,
    load,
)

MAINNET_SAFE = "0xA03be496e67Ec29bC62F01a428683D7F9c204930"
ARBITRUM_SAFE = "0x66331f0b9cb30d38779c786Bda5a3d57d12fbA50"
OTHER = Web3.to_checksum_address("0x" + "ba5e" * 10)


def word(value: int) -> bytes:
    return value.to_bytes(32, "big")


class TestTypeHashes(unittest.TestCase):
    def test_type_hashes_are_the_eip712_type_strings(self):
        self.assertEqual(
            DOMAIN_SEPARATOR_TYPEHASH,
            keccak(text="EIP712Domain(uint256 chainId,address verifyingContract)"),
        )
        self.assertEqual(
            SAFE_TX_TYPEHASH,
            keccak(
                text="SafeTx(address to,uint256 value,bytes data,uint8 operation,"
                "uint256 safeTxGas,uint256 baseGas,uint256 gasPrice,"
                "address gasToken,address refundReceiver,uint256 nonce)"
            ),
        )

    def test_exec_transaction_selector(self):
        self.assertEqual(
            EXEC_TRANSACTION_SELECTOR,
            keccak(
                text="execTransaction(address,uint256,bytes,uint8,uint256,uint256,"
                "uint256,address,address,bytes)"
            )[:4],
        )


class TestSafeTxHash(unittest.TestCase):
    def test_matches_the_hash_the_service_reported(self):
        """Safe v1.3.0 (mainnet), v1.3.0+L2 (arbitrum) and v1.4.1 (linea)."""
        for name in ALL_FIXTURES:
            recorded = load(name)
            with self.subTest(name):
                self.assertEqual(
                    recorded.transaction.safe_tx_hash(), recorded.reported_safe_tx_hash
                )

    def test_matches_safe_eth_py(self):
        for name in ALL_FIXTURES:
            tx = load(name).transaction
            with self.subTest(name):
                # safe-eth-py only tells versions before 1.0.0 and 1.3.0 apart;
                # every payout Safe is 1.3.0 or 1.4.1.
                reference = SafeTx(
                    None,
                    tx.safe,
                    tx.to,
                    tx.value,
                    HexBytes(tx.data),
                    tx.operation,
                    tx.safe_tx_gas,
                    tx.base_gas,
                    tx.gas_price,
                    tx.gas_token,
                    tx.refund_receiver,
                    safe_nonce=tx.nonce,
                    safe_version="1.3.0",
                    chain_id=tx.chain_id,
                )
                self.assertEqual(tx.safe_tx_hash(), bytes(reference.safe_tx_hash))

    def test_domain_separator_matches_the_contracts(self):
        """Values returned by domainSeparator() of these Safes on chain."""
        tx = load(MAINNET_COW).transaction
        for chain_id, safe, expected in (
            (
                1,
                MAINNET_SAFE,
                "9b82893c2d1751b917941fd7372b3246278113e8127d7a771bcb640391b00050",
            ),
            (
                42161,
                ARBITRUM_SAFE,
                "e6af797fdc261b750cb47585e78f35cb52f157ebb39bd26e29a0f0c5f85b0d7e",
            ),
            (
                59144,
                MAINNET_SAFE,
                "32db2f930bd6a21be0c3402eed5f1c2fe478263ebfcee3047197f8c90656ab22",
            ),
        ):
            with self.subTest(chain_id=chain_id):
                bound = dataclasses.replace(tx, chain_id=chain_id, safe=safe)
                self.assertEqual(bound.domain_separator().hex(), expected)

    def test_every_field_is_bound_by_the_hash(self):
        tx = load(ARBITRUM_NATIVE).transaction
        changes = {
            "chain_id": 1,
            "safe": OTHER,
            "to": OTHER,
            "value": 1,
            "data": tx.data + b"\x00",
            "operation": 0,
            "safe_tx_gas": 1,
            "base_gas": 1,
            "gas_price": 1,
            "gas_token": OTHER,
            "refund_receiver": OTHER,
            "nonce": tx.nonce + 1,
        }
        self.assertEqual(
            set(changes), {field.name for field in dataclasses.fields(SafeTransaction)}
        )
        for name, value in changes.items():
            with self.subTest(name):
                changed = dataclasses.replace(tx, **{name: value})
                self.assertNotEqual(changed.safe_tx_hash(), tx.safe_tx_hash())


class TestSafeTransactionFields(unittest.TestCase):
    def setUp(self):
        self.tx = load(LINEA_EMPTY).transaction

    def test_rejects_invalid_values(self):
        for name, value in (
            ("safe", OTHER.lower()),
            ("to", "0x1234"),
            ("value", -1),
            ("nonce", 2**256),
            ("gas_price", -1),
            ("chain_id", 0),
            ("operation", 2),
        ):
            with self.subTest(name):
                with self.assertRaises(ValueError):
                    dataclasses.replace(self.tx, **{name: value})


class TestFromTransactionService(unittest.TestCase):
    def setUp(self):
        self.record = dict(load(ARBITRUM_NATIVE).raw["safeTransaction"])

    def parse(self, **changes):
        return SafeTransaction.from_transaction_service(
            {**self.record, **changes}, 42161
        )

    def test_integers_as_json_numbers_or_decimal_strings(self):
        as_strings = self.parse(nonce="213", operation="1", safeTxGas="0")
        as_numbers = self.parse(value=0, gasPrice=0)
        self.assertEqual(as_strings, self.parse())
        self.assertEqual(as_numbers, self.parse())

    def test_null_data_is_empty(self):
        record = load(LINEA_EMPTY).raw["safeTransaction"]
        self.assertIsNone(record["data"])
        transaction, _ = SafeTransaction.from_transaction_service(record, 59144)
        self.assertEqual(transaction.data, b"")

    def test_rejects_malformed_records(self):
        for field, value in (
            ("value", "0012"),
            ("value", 1.0),
            ("nonce", True),
            ("nonce", -1),
            ("operation", 2),
            ("data", "0x8d80ff0a0"),
            ("data", "0x8d80 ff0a"),
            ("data", "8d80ff0a"),
            ("safe", "0x" + self.record["safe"][2:].upper()),
            ("safeTxHash", self.record["safeTxHash"][:-2]),
        ):
            with self.subTest(field=field, value=value):
                with self.assertRaises(ValueError):
                    self.parse(**{field: value})

    def test_rejects_missing_fields(self):
        record = dict(self.record)
        del record["refundReceiver"]
        with self.assertRaisesRegex(ValueError, "missing fields: refundReceiver"):
            SafeTransaction.from_transaction_service(record, 42161)


class TestDecodeExecTransaction(unittest.TestCase):
    def test_executed_calldata_is_the_proposed_transaction(self):
        for name in ALL_FIXTURES:
            recorded = load(name)
            if recorded.execution is None:
                continue
            with self.subTest(name):
                self.assertEqual(
                    recorded.execution["to"], recorded.transaction.safe.lower()
                )
                transaction, signatures = decode_exec_transaction(
                    bytes.fromhex(recorded.execution["input"][2:]),
                    chain_id=recorded.transaction.chain_id,
                    safe=recorded.transaction.safe,
                    nonce=recorded.transaction.nonce,
                )
                self.assertEqual(transaction, recorded.transaction)
                self.assertTrue(signatures)

    def encode(self, **changes) -> bytes:
        """Canonical execTransaction calldata for the Arbitrum payout."""
        tx = dataclasses.replace(load(ARBITRUM_NATIVE).transaction, **changes)
        signatures = b"\x11" * 65
        data_padded = tx.data + bytes(-len(tx.data) % 32)
        head = (
            bytes(12)
            + bytes.fromhex(tx.to[2:])
            + word(tx.value)
            + word(320)
            + word(tx.operation)
            + word(tx.safe_tx_gas)
            + word(tx.base_gas)
            + word(tx.gas_price)
            + bytes(12)
            + bytes.fromhex(tx.gas_token[2:])
            + bytes(12)
            + bytes.fromhex(tx.refund_receiver[2:])
            + word(320 + 32 + len(data_padded))
        )
        return (
            EXEC_TRANSACTION_SELECTOR
            + head
            + word(len(tx.data))
            + data_padded
            + word(len(signatures))
            + signatures
            + bytes(-len(signatures) % 32)
        )

    def decode(self, calldata: bytes):
        return decode_exec_transaction(
            calldata, chain_id=42161, safe=ARBITRUM_SAFE, nonce=213
        )

    def test_canonical_encoding_decodes(self):
        transaction, signatures = self.decode(self.encode())
        self.assertEqual(transaction, load(ARBITRUM_NATIVE).transaction)
        self.assertEqual(signatures, b"\x11" * 65)

    def test_rejects_non_canonical_encodings(self):
        valid = self.encode()

        def word_at(index: int) -> int:
            return 4 + 32 * index

        cases = {
            "selector": b"\x00" * 4 + valid[4:],
            "data offset": valid[: word_at(2)] + word(352) + valid[word_at(3) :],
            "signatures offset": valid[: word_at(9)] + word(0) + valid[word_at(10) :],
            "operation": valid[: word_at(3)] + word(2) + valid[word_at(4) :],
            "to padding": valid[: word_at(0)] + b"\x01" + valid[word_at(0) + 1 :],
            "gasToken padding": valid[: word_at(7)] + b"\x01" + valid[word_at(7) + 1 :],
            "refundReceiver padding": valid[: word_at(8)]
            + b"\x01"
            + valid[word_at(8) + 1 :],
            "trailing bytes": valid + bytes(32),
            "truncated": valid[:-1],
            "signature padding": valid[:-1] + b"\x01",
        }
        for name, calldata in cases.items():
            with self.subTest(name):
                with self.assertRaises(CalldataError):
                    self.decode(calldata)


if __name__ == "__main__":
    unittest.main()
