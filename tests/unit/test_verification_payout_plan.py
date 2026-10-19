"""Tests for src/verification/payout_plan.py."""

import copy
import hashlib
import json
import os
import tempfile
import unittest

from web3 import Web3

from src.config import Network
from src.verification.calldata import (
    Erc20Transfer,
    NativeTransfer,
    WrappedNativeWithdrawal,
)
from src.verification.payout_plan import (
    PayoutPlanError,
    load_payout_plan,
    parse_payout_plan,
    payout_plan_from_document,
    plan_hash,
)
from tests.unit.safe_transaction_fixtures import (
    ARBITRUM_NATIVE,
    LINEA_EMPTY,
    MAINNET_COW,
    load,
    plan_document,
    with_plan_hash,
)

OTHER = Web3.to_checksum_address("0x" + "ba5e" * 10)


def rehashed(document: dict) -> str:
    return json.dumps(with_plan_hash(document))


class TestValidPlans(unittest.TestCase):
    def test_arbitrum_native_plan(self):
        document = plan_document(load(ARBITRUM_NATIVE))
        plan = parse_payout_plan(json.dumps(document, indent=4))
        self.assertEqual(plan.chain_id, 42161)
        self.assertEqual(plan.safe, "0x66331f0b9cb30d38779c786Bda5a3d57d12fbA50")
        self.assertEqual(plan.nonce, 213)
        self.assertEqual(plan.to, "0x40A2aCCbd92BCA938b02010E17A5b8929b49130D")
        self.assertEqual(plan.operation, 1)
        self.assertEqual(plan.plan_hash, document["planHash"])
        self.assertEqual(len(plan.calls), 24)
        self.assertEqual(
            plan.calls[0],
            WrappedNativeWithdrawal(
                Web3.to_checksum_address("0x82af49447d8a07e3bd95bd0d56f35241523fbab1"),
                6435645361627000999,
            ),
        )
        self.assertTrue(all(isinstance(c, NativeTransfer) for c in plan.calls[1:]))

    def test_mainnet_cow_plan(self):
        plan = parse_payout_plan(json.dumps(plan_document(load(MAINNET_COW))))
        self.assertEqual(len(plan.calls), 31)
        self.assertTrue(all(isinstance(c, Erc20Transfer) for c in plan.calls))
        self.assertEqual(sum(c.amount for c in plan.calls), 12081043070982411514571)

    def test_empty_transaction_plan(self):
        plan = parse_payout_plan(json.dumps(plan_document(load(LINEA_EMPTY))))
        self.assertEqual((plan.operation, plan.calls, plan.to), (0, (), plan.safe))

    def test_lowercase_addresses_are_checksummed(self):
        document = plan_document(load(ARBITRUM_NATIVE))
        document["safe"] = document["safe"].lower()
        plan = parse_payout_plan(rehashed(document))
        self.assertEqual(plan.safe, "0x66331f0b9cb30d38779c786Bda5a3d57d12fbA50")

    def test_load_from_file(self):
        document = plan_document(load(MAINNET_COW))
        with tempfile.TemporaryDirectory() as directory:
            path = os.path.join(directory, "plan.json")
            with open(path, "w", encoding="utf-8") as file:
                json.dump(document, file)
            self.assertEqual(
                load_payout_plan(path), parse_payout_plan(json.dumps(document))
            )

    def test_every_network_name_is_accepted(self):
        document = plan_document(load(LINEA_EMPTY))
        for network in Network:
            with self.subTest(network.value):
                plan = parse_payout_plan(
                    rehashed({**document, "network": network.value})
                )
                self.assertEqual(plan.network, network.value)


class TestPlanHash(unittest.TestCase):
    def setUp(self):
        self.document = plan_document(load(ARBITRUM_NATIVE))

    def test_independent_of_formatting_and_key_order(self):
        reordered = dict(reversed(list(self.document.items())))
        for text in (
            json.dumps(self.document),
            json.dumps(self.document, indent=2, sort_keys=True),
            json.dumps(reordered, separators=(" , ", " : ")),
        ):
            with self.subTest(text[:40]):
                self.assertEqual(
                    parse_payout_plan(text).plan_hash, self.document["planHash"]
                )

    def test_canonical_serialisation(self):
        body = {k: v for k, v in self.document.items() if k != "planHash"}
        canonical = json.dumps(body, sort_keys=True, separators=(",", ":"))
        self.assertEqual(
            plan_hash(self.document),
            "0x" + hashlib.sha256(canonical.encode("ascii")).hexdigest(),
        )

    def test_any_change_is_detected(self):
        changes = {
            "runId": "another-run",
            "nonce": 214,
            "calls": self.document["calls"][1:],
        }
        for key, value in changes.items():
            with self.subTest(key):
                with self.assertRaisesRegex(PayoutPlanError, "planHash: declared"):
                    parse_payout_plan(json.dumps({**self.document, key: value}))
        edited = copy.deepcopy(self.document)
        edited["calls"][5]["amountAtoms"] = str(
            int(edited["calls"][5]["amountAtoms"]) + 1
        )
        with self.assertRaisesRegex(PayoutPlanError, "planHash: declared"):
            parse_payout_plan(json.dumps(edited))

    def test_malformed_plan_hash(self):
        for value in ("0x" + "AB" * 32, "ab" * 32, "0x1234", 7):
            with self.subTest(value):
                with self.assertRaisesRegex(PayoutPlanError, "planHash"):
                    parse_payout_plan(json.dumps({**self.document, "planHash": value}))


class TestRejectedPlans(unittest.TestCase):
    """Anything outside the schema is rejected, never coerced."""

    def setUp(self):
        self.document = plan_document(load(ARBITRUM_NATIVE))
        self.erc20 = plan_document(load(MAINNET_COW))
        self.empty = plan_document(load(LINEA_EMPTY))

    def assert_rejected(self, text: str, message: str) -> None:
        with self.assertRaisesRegex(PayoutPlanError, message):
            parse_payout_plan(text)

    def replace_in_text(self, old: str, new: str, document=None) -> str:
        text = json.dumps(document or self.document)
        self.assertIn(old, text)
        return text.replace(old, new, 1)

    def test_floating_point_amounts(self):
        amount = self.document["calls"][1]["amountAtoms"]
        for literal in ("68168977168730428.0", "6.8168977168730428e16", "1e21"):
            with self.subTest(literal):
                self.assert_rejected(
                    self.replace_in_text(f'"{amount}"', literal), "floating-point"
                )

    def test_floating_point_anywhere(self):
        self.assert_rejected(
            self.replace_in_text('"nonce": 213', '"nonce": 213.0'), "floating-point"
        )
        self.assert_rejected(
            self.replace_in_text('"chainId": 42161', '"chainId": 4.2161e4'),
            "floating-point",
        )

    def test_non_finite_numbers(self):
        for literal in ("NaN", "Infinity", "-Infinity"):
            with self.subTest(literal):
                self.assert_rejected(
                    self.replace_in_text('"nonce": 213', f'"nonce": {literal}'),
                    f"{literal} is not allowed",
                )

    def test_amount_as_json_integer(self):
        amount = self.document["calls"][1]["amountAtoms"]
        self.assert_rejected(
            self.replace_in_text(f'"{amount}"', amount), "decimal string"
        )

    def test_non_canonical_amount_strings(self):
        for amount in (
            "068168977168730428",
            "+68168977168730428",
            " 68168977168730428",
            "68_168_977_168_730_428",
            "١٢",
            "0x10",
            "",
            "-5",
            str(2**256),
        ):
            with self.subTest(amount):
                document = copy.deepcopy(self.document)
                document["calls"][1]["amountAtoms"] = amount
                self.assert_rejected(rehashed(document), r"calls\[1\].amountAtoms")

    def test_zero_amount(self):
        document = copy.deepcopy(self.document)
        document["calls"][1]["amountAtoms"] = "0"
        self.assert_rejected(rehashed(document), "greater than zero")

    def test_duplicate_keys(self):
        self.assert_rejected(
            self.replace_in_text('"nonce": 213', '"nonce": 213, "nonce": 214'),
            "duplicate key 'nonce'",
        )
        amount = self.document["calls"][1]["amountAtoms"]
        self.assert_rejected(
            self.replace_in_text(
                f'"amountAtoms": "{amount}"',
                f'"amountAtoms": "{amount}", "amountAtoms": "1"',
            ),
            "duplicate key 'amountAtoms'",
        )

    def test_unknown_and_missing_members(self):
        self.assert_rejected(
            rehashed({**self.document, "extra": 1}), "plan: unknown extra"
        )
        document = dict(self.document)
        del document["configHash"]
        self.assert_rejected(rehashed(document), "plan: missing configHash")
        document = copy.deepcopy(self.document)
        document["calls"][1]["token"] = OTHER
        self.assert_rejected(rehashed(document), r"calls\[1\]: unknown token")
        document = copy.deepcopy(self.erc20)
        del document["calls"][0]["token"]
        self.assert_rejected(rehashed(document), r"calls\[0\]: missing token")

    def test_unknown_call_type(self):
        for call_type in ("erc20transfer", "nativetransfer", "addOverdraft", None, 1):
            with self.subTest(call_type):
                document = copy.deepcopy(self.document)
                document["calls"][1]["callType"] = call_type
                self.assert_rejected(rehashed(document), "unknown callType")

    def test_addresses(self):
        for address in (
            "0x66331f0b9cb30d38779c786Bda5a3d57d12fbA5O",  # letter O
            "0x66331F0b9cb30d38779c786Bda5a3d57d12fbA50",  # checksum typo
            "0x66331f0b9cb30d38779c786bda5a3d57d12fba5",
            "66331f0b9cb30d38779c786bda5a3d57d12fba50",
        ):
            with self.subTest(address):
                self.assert_rejected(
                    rehashed({**self.document, "safe": address}), "safe"
                )

    def test_integers(self):
        for key, value in (
            ("schemaVersion", 2),
            ("schemaVersion", "1"),
            ("schemaVersion", True),
            ("chainId", 0),
            ("chainId", -1),
            ("chainId", "42161"),
            ("nonce", -1),
            ("nonce", "213"),
            ("nonce", False),
            ("operation", 2),
            ("operation", "1"),
        ):
            with self.subTest(key=key, value=value):
                self.assert_rejected(rehashed({**self.document, key: value}), key)

    def test_metadata_formats(self):
        for key, value in (
            ("runId", ""),
            ("runId", "run id with spaces"),
            ("runId", "x" * 129),
            ("network", "Arbitrum"),
            ("network", ""),
            ("accountingPeriod", "2026-06-16"),
            ("accountingPeriod", "2026-06-16-to-2026-06-09"),
            ("accountingPeriod", "2026-02-30-to-2026-03-06"),
            ("accountingPeriod", "2026-6-9-to-2026-6-16"),
            ("generatorCommit", "e9dbef3"),
            ("generatorCommit", "E" * 40),
            ("configHash", "ab" * 32),
            ("configHash", "0x" + "AB" * 32),
        ):
            with self.subTest(key=key, value=value):
                self.assert_rejected(rehashed({**self.document, key: value}), key)

    def test_structure(self):
        for text in ("[]", '"plan"', "null", "{"):
            with self.subTest(text):
                with self.assertRaises(PayoutPlanError):
                    parse_payout_plan(text)
        self.assert_rejected(
            rehashed({**self.document, "calls": {}}), "calls: expected a JSON array"
        )
        document = copy.deepcopy(self.document)
        document["calls"][0] = "withdraw"
        self.assert_rejected(rehashed(document), r"calls\[0\]: unknown callType")

    def test_multisend_needs_calls(self):
        self.assert_rejected(
            rehashed({**self.document, "calls": []}), "at least one call"
        )

    def test_empty_transaction_rules(self):
        self.assert_rejected(
            rehashed({**self.empty, "calls": self.document["calls"][1:2]}),
            "must be empty and call the Safe",
        )
        self.assert_rejected(
            rehashed({**self.empty, "to": OTHER}), "must be empty and call the Safe"
        )

    def test_at_most_one_withdrawal(self):
        document = copy.deepcopy(self.document)
        document["calls"].append(document["calls"][0])
        self.assert_rejected(rehashed(document), "2 wrapped native withdrawals")

    def test_document_must_be_parsed_json(self):
        with self.assertRaisesRegex(PayoutPlanError, "expected a JSON object"):
            payout_plan_from_document([self.document])


if __name__ == "__main__":
    unittest.main()
