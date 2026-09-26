"""Checks the recorded Safe transaction fixtures against the public record.

The strict verifier's unit tests run offline from the JSON fixtures in
tests/fixtures/safe_transactions/. Every fixture is a real payout Safe
transaction, recorded by ``record_fixture`` from the Safe Transaction Service
(the transaction and Safe's own decoding of its MultiSend) and, when it was
executed, from the chain (the execTransaction calldata). These tests record
them again and require the committed files to be identical. They also check
the recomputed safeTxHash against the Safe contract's own getTransactionHash
and the MultiSendCallOnly code on each fixture's chain.

The tests need network access and are skipped when a service is unreachable.
SAFE_API_KEY, if set, is sent to the Safe Transaction Service.
To re-record a fixture, call ``write_fixture(name)``.
"""

from __future__ import annotations

import json
import os
import unittest
from dataclasses import dataclass
from pathlib import Path
from typing import Any

import requests
from eth_abi import encode
from eth_utils.crypto import keccak

from src.verification.safe_transaction import SafeTransaction

FIXTURE_DIR = Path(__file__).parent.parent / "fixtures" / "safe_transactions"
SAFE_API = "https://api.safe.global/tx-service/{service}/api/v1"
RPC_URLS = {
    1: "https://ethereum-rpc.publicnode.com",
    42161: "https://arbitrum-one-rpc.publicnode.com",
    59144: "https://linea-rpc.publicnode.com",
}
MULTISEND_CALL_ONLY = "0x40A2aCCbd92BCA938b02010E17A5b8929b49130D"
# keccak256 of the MultiSendCallOnly v1.3.0 runtime code, identical on every
# network the payout Safes are on.
MULTISEND_CALL_ONLY_CODE_HASH = (
    "a9865ac2d9c7a1591619b188c4d88167b50df6cc0c5327fcbd1c8c75f7c066ad"
)
SAFE_TRANSACTION_FIELDS = (
    "safe",
    "to",
    "value",
    "data",
    "operation",
    "safeTxGas",
    "baseGas",
    "gasPrice",
    "gasToken",
    "refundReceiver",
    "nonce",
    "safeTxHash",
    "isExecuted",
    "origin",
    "submissionDate",
)


@dataclass(frozen=True)
class FixtureSpec:
    """Where a fixture comes from."""

    service: str
    chain_id: int
    safe_tx_hash: str
    description: str


FIXTURES = {
    "mainnet-cow-payout-nonce-1186.json": FixtureSpec(
        "eth",
        1,
        "0x8b3c6d34c8846f8ca00913098e1367ae510d0fa3fc6ae32322f97a220c182b67",
        "COW reward payout on mainnet for the 2026-06-16 Arbitrum payout run: "
        "31 ERC-20 transfers of COW.",
    ),
    "arbitrum-native-payout-nonce-213.json": FixtureSpec(
        "arb1",
        42161,
        "0xc842fd6efa89e875225facc062c0718b24c7ec540dcabb3aa24f5da23a3c8009",
        "Native payout on Arbitrum for the 2026-06-16 payout run, as executed: "
        "a WETH withdraw followed by 23 native transfers.",
    ),
    "arbitrum-native-payout-nonce-213-superseded.json": FixtureSpec(
        "arb1",
        42161,
        "0xfea75cc8e8567336f9599b226eda4df00cde7e7e2dd843547e4f4cc79d4a08b8",
        "Earlier proposal for the same Safe and nonce as "
        "arbitrum-native-payout-nonce-213.json, from a previous run of the "
        "payout script: a WETH withdraw followed by 24 native transfers. "
        "It was superseded and never executed.",
    ),
    "arbitrum-overdrafts-nonce-214.json": FixtureSpec(
        "arb1",
        42161,
        "0xfa28a71c1cedffd045b8c17efaba82dffd01eb626874f7eb06ce68962a5a2011",
        "Overdrafts transaction on Arbitrum for the 2026-06-16 payout run: "
        "5 addOverdraft calls, which the strict verifier does not cover.",
    ),
    "linea-native-payout-nonce-61.json": FixtureSpec(
        "linea",
        59144,
        "0x2669ef800b7efb9ac290f889095b7569994f1db9d11f994649e11b1d653693b6",
        "Native payout on Linea (Safe v1.4.1) without a WETH withdraw: "
        "7 native transfers.",
    ),
    "linea-empty-nonce-75.json": FixtureSpec(
        "linea",
        59144,
        "0x2235f918ac3f787fffd8ba59cd98e14ffc002c62afb6bf363814b756944896a5",
        "Empty nonce-reservation transaction on Linea (Safe v1.4.1).",
    ),
}


def _request(method: str, url: str, **kwargs: Any) -> Any:
    headers = {"User-Agent": "solver-rewards-tests"}
    if kwargs.pop("safe_api", False) and os.environ.get("SAFE_API_KEY"):
        headers["Authorization"] = f"Bearer {os.environ['SAFE_API_KEY']}"
    try:
        response = requests.request(method, url, headers=headers, timeout=30, **kwargs)
    except requests.RequestException as err:
        raise unittest.SkipTest(f"{url} unreachable: {err}") from err
    if response.status_code in (401, 403, 404, 429) or response.status_code >= 500:
        raise unittest.SkipTest(f"{url} answered HTTP {response.status_code}")
    response.raise_for_status()
    return response.json()


def rpc(chain_id: int, method: str, params: list[Any]) -> Any:
    """JSON-RPC call to a public node of ``chain_id``."""
    reply = _request(
        "POST",
        RPC_URLS[chain_id],
        json={"jsonrpc": "2.0", "id": 1, "method": method, "params": params},
    )
    if "error" in reply:
        raise unittest.SkipTest(f"{method} on chain {chain_id}: {reply['error']}")
    return reply["result"]


def _decoded(data_decoded: dict[str, Any] | None) -> dict[str, Any] | None:
    if data_decoded is None:
        return None
    return {
        "method": data_decoded["method"],
        "parameters": [
            {key: parameter[key] for key in ("name", "type", "value")}
            for parameter in data_decoded["parameters"]
        ],
    }


def record_fixture(spec: FixtureSpec) -> dict[str, Any]:
    """Record a fixture from the Safe Transaction Service and the chain."""
    record = _request(
        "GET",
        f"{SAFE_API.format(service=spec.service)}"
        f"/multisig-transactions/{spec.safe_tx_hash}/",
        safe_api=True,
    )
    inner = None
    if record["operation"] == 1:
        (parameter,) = record["dataDecoded"]["parameters"]
        inner = [
            {
                "operation": entry["operation"],
                "to": entry["to"],
                "value": entry["value"],
                "data": entry["data"],
                "dataDecoded": _decoded(entry["dataDecoded"]),
            }
            for entry in parameter["valueDecoded"]
        ]
    execution = None
    if record["isExecuted"]:
        onchain = rpc(
            spec.chain_id, "eth_getTransactionByHash", [record["transactionHash"]]
        )
        execution = {
            "transactionHash": record["transactionHash"],
            "blockNumber": record["blockNumber"],
            "to": onchain["to"],
            "input": onchain["input"],
        }
    return {
        "description": spec.description,
        "transactionService": spec.service,
        "chainId": spec.chain_id,
        "safeTransaction": {key: record[key] for key in SAFE_TRANSACTION_FIELDS},
        "multiSendTransactions": inner,
        "execution": execution,
    }


def write_fixture(name: str) -> None:
    """(Re-)record fixture ``name`` into the fixture directory."""
    fixture = record_fixture(FIXTURES[name])
    (FIXTURE_DIR / name).write_text(json.dumps(fixture, indent=2) + "\n", "utf-8")


class TestRecordedFixtures(unittest.TestCase):
    """The committed fixtures are the public record of these transactions."""

    def test_every_fixture_file_has_a_source(self) -> None:
        self.assertEqual(
            sorted(path.name for path in FIXTURE_DIR.glob("*.json")), sorted(FIXTURES)
        )

    def test_fixtures_match_the_public_record(self) -> None:
        for name, spec in FIXTURES.items():
            with self.subTest(name):
                committed = json.loads((FIXTURE_DIR / name).read_text("utf-8"))
                self.assertEqual(record_fixture(spec), committed)

    def test_contract_computes_the_same_safe_tx_hash(self) -> None:
        signature = (
            "getTransactionHash(address,uint256,bytes,uint8,uint256,uint256,"
            "uint256,address,address,uint256)"
        )
        for name, spec in FIXTURES.items():
            with self.subTest(name):
                record = json.loads((FIXTURE_DIR / name).read_text("utf-8"))
                transaction, _ = SafeTransaction.from_transaction_service(
                    record["safeTransaction"], spec.chain_id
                )
                arguments = encode(
                    signature[signature.index("(") + 1 : -1].split(","),
                    [
                        transaction.to,
                        transaction.value,
                        transaction.data,
                        transaction.operation,
                        transaction.safe_tx_gas,
                        transaction.base_gas,
                        transaction.gas_price,
                        transaction.gas_token,
                        transaction.refund_receiver,
                        transaction.nonce,
                    ],
                )
                call = "0x" + (keccak(text=signature)[:4] + arguments).hex()
                result = rpc(
                    spec.chain_id,
                    "eth_call",
                    [{"to": transaction.safe, "data": call}, "latest"],
                )
                self.assertEqual(result, "0x" + transaction.safe_tx_hash().hex())

    def test_multisend_call_only_code_is_the_same_on_every_fixture_chain(
        self,
    ) -> None:
        for chain_id in sorted({spec.chain_id for spec in FIXTURES.values()}):
            with self.subTest(chain_id=chain_id):
                code = rpc(chain_id, "eth_getCode", [MULTISEND_CALL_ONLY, "latest"])
                self.assertEqual(
                    keccak(hexstr=code).hex(), MULTISEND_CALL_ONLY_CODE_HASH
                )


if __name__ == "__main__":
    unittest.main()
