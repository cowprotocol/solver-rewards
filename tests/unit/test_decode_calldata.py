"""Tests for src/verification/decode_calldata.py."""

import csv
import json
import os
import tempfile
import unittest

from eth_abi import encode
from safe_eth.safe.multi_send import MultiSendOperation, MultiSendTx

from src.abis.load import erc20, overdraftsmanager
from src.verification.decode_calldata import (
    decode_overdrafts,
    decode_transfers,
    extract_calldata,
    write_overdrafts_csv,
    write_transfers_csv,
)

_ERC20 = erc20()
_OVERDRAFTS = overdraftsmanager()
_COW = "0xdef1ca1fb7fbcdc777520aa7f396b4e015f497ab"


def _build_multisend(txs: list[MultiSendTx]) -> str:
    """Builds multisend calldata (with selector) without needing a live RPC client."""
    packed = b"".join(bytes(t.encoded_data) for t in txs)
    return "0x" + (bytes.fromhex("8d80ff0a") + encode(["bytes"], [packed])).hex()


def _erc20_transfer_tx(to: str, amount_wei: int) -> MultiSendTx:
    data = _ERC20.encode_abi(abi_element_identifier="transfer", args=[to, amount_wei])
    return MultiSendTx(
        operation=MultiSendOperation.CALL,
        to="0x0000000000000000000000000000000000000009",
        value=0,
        data=data,
    )


def _native_tx(to: str, amount_wei: int) -> MultiSendTx:
    return MultiSendTx(
        operation=MultiSendOperation.CALL, to=to, value=amount_wei, data="0x"
    )


def _weth_withdraw_tx(amount_wei: int) -> MultiSendTx:
    from src.abis.load import weth9

    weth = weth9()
    data = weth.encode_abi(abi_element_identifier="withdraw", args=[amount_wei])
    return MultiSendTx(
        operation=MultiSendOperation.CALL,
        to="0x000000000000000000000000000000000000dead",
        value=0,
        data=data,
    )


def _overdraft_tx(account: str, amount_wei: int) -> MultiSendTx:
    data = _OVERDRAFTS.encode_abi(
        abi_element_identifier="addOverdraft", args=[account, amount_wei]
    )
    return MultiSendTx(
        operation=MultiSendOperation.CALL,
        to="0x0000000000000000000000000000000000000abc",
        value=0,
        data=data,
    )


_RECEIVER_1 = "0x0000000000000000000000000000000000000001"
_RECEIVER_2 = "0x0000000000000000000000000000000000000002"


class TestExtractCalldata(unittest.TestCase):
    def test_bare_hex_passthrough(self):
        self.assertEqual(extract_calldata(" 0xabc123 "), "0xabc123")

    def test_json_extracts_data_field(self):
        raw = json.dumps({"to": "0xsafe", "data": "0xdeadbeef", "nonce": 5})
        self.assertEqual(extract_calldata(raw), "0xdeadbeef")

    def test_empty_raises(self):
        with self.assertRaises(ValueError):
            extract_calldata("   ")

    def test_json_without_data_field_raises(self):
        with self.assertRaises(KeyError):
            extract_calldata(json.dumps({"to": "0xsafe"}))


class TestDecodeTransfers(unittest.TestCase):
    def test_native_transfers_decoded(self):
        calldata = _build_multisend(
            [_native_tx(_RECEIVER_1, 10**18), _native_tx(_RECEIVER_2, 5 * 10**17)]
        )
        transfers = decode_transfers(calldata, "native", _COW)
        self.assertEqual(len(transfers), 2)
        self.assertEqual(transfers[0].receiver, _RECEIVER_1.lower())
        self.assertAlmostEqual(transfers[0].amount, 1.0)
        self.assertAlmostEqual(transfers[1].amount, 0.5)
        self.assertTrue(all(t.token_type == "native" for t in transfers))

    def test_weth_unwrap_is_skipped(self):
        calldata = _build_multisend(
            [_weth_withdraw_tx(10**18), _native_tx(_RECEIVER_1, 10**18)]
        )
        transfers = decode_transfers(calldata, "native", _COW)
        self.assertEqual(len(transfers), 1)
        self.assertEqual(transfers[0].receiver, _RECEIVER_1.lower())

    def test_erc20_transfers_decoded(self):
        calldata = _build_multisend(
            [
                _erc20_transfer_tx(_RECEIVER_1, 100 * 10**18),
                _erc20_transfer_tx(_RECEIVER_2, 42 * 10**18),
            ]
        )
        transfers = decode_transfers(calldata, "erc20", _COW)
        self.assertEqual(len(transfers), 2)
        self.assertTrue(all(t.token_type == "erc20" for t in transfers))
        self.assertTrue(all(t.token_address == _COW for t in transfers))
        self.assertAlmostEqual(transfers[0].amount, 100.0)
        self.assertAlmostEqual(transfers[1].amount, 42.0)

    def test_accepts_full_safe_tx_json(self):
        calldata = _build_multisend([_native_tx(_RECEIVER_1, 10**18)])
        raw = json.dumps({"to": "0xsafe", "data": calldata, "nonce": 1})
        transfers = decode_transfers(raw, "native", _COW)
        self.assertEqual(len(transfers), 1)

    def test_invalid_token_type_raises(self):
        with self.assertRaises(ValueError):
            decode_transfers("0x", "cow", _COW)


class TestDecodeOverdrafts(unittest.TestCase):
    def test_overdrafts_decoded(self):
        calldata = _build_multisend(
            [
                _overdraft_tx(_RECEIVER_1, 10**17),
                _native_tx(_RECEIVER_2, 10**18),  # unrelated tx, should be ignored
                _overdraft_tx(_RECEIVER_2, 3 * 10**17),
            ]
        )
        entries = decode_overdrafts(calldata)
        self.assertEqual(len(entries), 2)
        self.assertEqual(entries[0].account, _RECEIVER_1.lower())
        self.assertAlmostEqual(entries[0].amount, 0.1)
        self.assertAlmostEqual(entries[1].amount, 0.3)


class TestWriteCsvHelpers(unittest.TestCase):
    def test_write_transfers_csv_roundtrips(self):
        calldata = _build_multisend([_native_tx(_RECEIVER_1, 10**18)])
        transfers = decode_transfers(calldata, "native", _COW)
        path = tempfile.mktemp(suffix=".csv")
        try:
            write_transfers_csv(transfers, path)
            with open(path, newline="", encoding="utf-8") as f:
                rows = list(csv.DictReader(f))
            self.assertEqual(len(rows), 1)
            self.assertEqual(rows[0]["token_type"], "native")
            self.assertEqual(rows[0]["receiver"], _RECEIVER_1.lower())
            self.assertAlmostEqual(float(rows[0]["amount"]), 1.0)
        finally:
            if os.path.exists(path):
                os.remove(path)

    def test_write_overdrafts_csv(self):
        calldata = _build_multisend([_overdraft_tx(_RECEIVER_1, 10**17)])
        entries = decode_overdrafts(calldata)
        path = tempfile.mktemp(suffix=".csv")
        try:
            write_overdrafts_csv(entries, path)
            with open(path, newline="", encoding="utf-8") as f:
                rows = list(csv.DictReader(f))
            self.assertEqual(len(rows), 1)
            self.assertEqual(rows[0]["account"], _RECEIVER_1.lower())
            self.assertAlmostEqual(float(rows[0]["amount"]), 0.1)
        finally:
            if os.path.exists(path):
                os.remove(path)


if __name__ == "__main__":
    unittest.main()
