"""Recorded payout Safe transactions for the strict verifier tests.

The fixtures in tests/fixtures/safe_transactions/ are real payout transactions
(see tests/e2e/test_strict_verifier_fixtures.py for their sources). Each one
holds the transaction as the Safe Transaction Service returns it, Safe's own
decoding of its MultiSend and, if it was executed, the execTransaction
calldata from the chain.

The fixture boundary is the list of MultiSendTx that post_multisend() is given:
``multisend_txs`` rebuilds it from Safe's decoding, and ``producer_encoding``
encodes it exactly like the payout script does. Expected plans are built from
Safe's decoding, never from the decoder under test.
"""

from __future__ import annotations

import json
from dataclasses import dataclass
from pathlib import Path
from typing import Any

from hexbytes import HexBytes
from safe_eth.eth.contracts import get_multi_send_contract
from safe_eth.safe.multi_send import MultiSendOperation, MultiSendTx
from web3 import Web3

from src.verification.payout_plan import PayoutPlan, parse_payout_plan, plan_hash
from src.verification.safe_transaction import SafeTransaction

FIXTURE_DIR = Path(__file__).parent.parent / "fixtures" / "safe_transactions"

MAINNET_COW = "mainnet-cow-payout-nonce-1186.json"
MAINNET_NATIVE = "mainnet-native-payout-nonce-1466.json"
ARBITRUM_NATIVE = "arbitrum-native-payout-nonce-213.json"
ARBITRUM_NATIVE_SUPERSEDED = "arbitrum-native-payout-nonce-213-superseded.json"
ARBITRUM_OVERDRAFTS = "arbitrum-overdrafts-nonce-214.json"
LINEA_NATIVE = "linea-native-payout-nonce-61.json"
LINEA_EMPTY = "linea-empty-nonce-75.json"

ALL_FIXTURES = [
    MAINNET_COW,
    MAINNET_NATIVE,
    ARBITRUM_NATIVE,
    ARBITRUM_NATIVE_SUPERSEDED,
    ARBITRUM_OVERDRAFTS,
    LINEA_NATIVE,
    LINEA_EMPTY,
]
# Fixtures whose every call has a plan representation.
PLANNABLE_FIXTURES = [
    MAINNET_COW,
    MAINNET_NATIVE,
    ARBITRUM_NATIVE,
    ARBITRUM_NATIVE_SUPERSEDED,
    LINEA_NATIVE,
    LINEA_EMPTY,
]

# Historical transactions carry no plan metadata; these values only satisfy
# the schema and are not verified against anything.
_NETWORKS = {1: "mainnet", 42161: "arbitrum", 59144: "linea"}
TEST_METADATA = {
    "schemaVersion": 1,
    "accountingPeriod": "2026-06-09-to-2026-06-16",
    "generatorCommit": "0123456789abcdef0123456789abcdef01234567",
    "configHash": "0x" + "ab" * 32,
}


@dataclass(frozen=True)
class RecordedTransaction:
    """A fixture, parsed."""

    name: str
    raw: dict[str, Any]
    transaction: SafeTransaction
    reported_safe_tx_hash: bytes

    @property
    def inner(self) -> list[dict[str, Any]]:
        """Safe's decoding of the MultiSend's inner transactions."""
        entries: list[dict[str, Any]] = self.raw["multiSendTransactions"] or []
        return entries

    @property
    def execution(self) -> dict[str, Any] | None:
        """The executed transaction on chain, if any."""
        execution: dict[str, Any] | None = self.raw["execution"]
        return execution


def load(name: str) -> RecordedTransaction:
    """Load and parse a fixture."""
    raw = json.loads((FIXTURE_DIR / name).read_text("utf-8"))
    transaction, reported = SafeTransaction.from_transaction_service(
        raw["safeTransaction"], raw["chainId"]
    )
    return RecordedTransaction(name, raw, transaction, reported)


def multisend_txs(recorded: RecordedTransaction) -> list[MultiSendTx]:
    """The MultiSendTx list the payout script handed to post_multisend()."""
    return [
        MultiSendTx(
            operation=MultiSendOperation(entry["operation"]),
            to=Web3.to_checksum_address(entry["to"]),
            value=int(entry["value"]),
            data=HexBytes(entry["data"] or b""),
        )
        for entry in recorded.inner
    ]


def producer_encoding(transactions: list[MultiSendTx]) -> bytes:
    """Encode transactions like build_encoded_multisend(), without a node.

    build_encoded_multisend() calls MultiSend.build_tx_data(), which ABI
    encodes multiSend(b"".join(tx.encoded_data for tx in transactions)) and
    needs a node only to fill in unused transaction fields.
    """
    packed = b"".join(transaction.encoded_data for transaction in transactions)
    encoded = get_multi_send_contract(Web3()).encode_abi(
        abi_element_identifier="multiSend", args=[packed]
    )
    return bytes(HexBytes(encoded))


def _parameters(entry: dict[str, Any], method: str, types: list[str]) -> list[str]:
    decoded = entry["dataDecoded"]
    assert decoded["method"] == method, decoded
    assert [parameter["type"] for parameter in decoded["parameters"]] == types
    return [str(parameter["value"]) for parameter in decoded["parameters"]]


def planned_calls(recorded: RecordedTransaction) -> list[dict[str, str]]:
    """Plan calls for a fixture, derived from Safe's own decoding of it."""
    calls = []
    for entry in recorded.inner:
        if entry["data"] is None:
            calls.append(
                {
                    "callType": "nativeTransfer",
                    "recipient": entry["to"],
                    "amountAtoms": entry["value"],
                }
            )
        elif entry["dataDecoded"]["method"] == "transfer":
            recipient, amount = _parameters(entry, "transfer", ["address", "uint256"])
            calls.append(
                {
                    "callType": "erc20Transfer",
                    "token": entry["to"],
                    "recipient": recipient,
                    "amountAtoms": amount,
                }
            )
        else:
            (amount,) = _parameters(entry, "withdraw", ["uint256"])
            calls.append(
                {
                    "callType": "wrappedNativeWithdrawal",
                    "token": entry["to"],
                    "amountAtoms": amount,
                }
            )
    return calls


def with_plan_hash(document: dict[str, Any]) -> dict[str, Any]:
    """The document with its planHash (re)computed."""
    return {**document, "planHash": plan_hash(document)}


def plan_document(recorded: RecordedTransaction) -> dict[str, Any]:
    """The plan the payout script would emit for a fixture."""
    record = recorded.raw["safeTransaction"]
    return with_plan_hash(
        {
            **TEST_METADATA,
            "runId": "fixture-" + recorded.name.removesuffix(".json"),
            "network": _NETWORKS[recorded.raw["chainId"]],
            "chainId": recorded.raw["chainId"],
            "safe": record["safe"],
            "nonce": record["nonce"],
            "to": record["to"],
            "operation": record["operation"],
            "calls": planned_calls(recorded),
        }
    )


def plan_for(recorded: RecordedTransaction) -> PayoutPlan:
    """The fixture's plan, read back from JSON like a plan file."""
    return parse_payout_plan(json.dumps(plan_document(recorded), indent=2))
