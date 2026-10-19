"""Tests for src/verification/plan_builder.py.

Plans are built from the expected calls of src/verification/expected_calls.py,
which are derived from Transfer objects, the payout intent.
"""

import dataclasses
import hashlib
import json
import os
import subprocess
import sys
import unittest
from collections import Counter
from pathlib import Path
from unittest import mock

from dune_client.types import Address
from eth_utils.address import is_checksum_address

from src.models.token import Token
from src.models.transfer import Transfer
from src.verification.calldata import (
    Erc20Transfer,
    NativeTransfer,
    WrappedNativeWithdrawal,
)
from src.verification.expected_calls import (
    cow_multisend_calls,
    expected_unwrap,
    native_multisend_calls,
    transfer_calls,
)
from src.verification.payout_plan import (
    PayoutPlanError,
    parse_payout_plan,
    payout_plan_from_document,
    plan_hash,
)
from src.verification.plan_builder import (
    BuiltPlan,
    PlanProvenance,
    empty_transaction_plan,
    multisend_plan,
)
from src.verification.strict_verifier import (
    APPROVED_MULTISEND_CONTRACTS,
    verify_safe_transaction,
)
from tests.unit.safe_transaction_fixtures import (
    MAINNET_NATIVE,
    PLANNABLE_FIXTURES,
    RecordedTransaction,
    load,
    planned_calls,
)

# The MultiSendCallOnly contract post_multisend() targets.
MULTISEND_CALL_ONLY = "0x40A2aCCbd92BCA938b02010E17A5b8929b49130D"
MAINNET_SAFE = "0xA03be496e67Ec29bC62F01a428683D7F9c204930"
COW = "0xDEf1CA1fb7FBcDC777520aa7f396b4E015F497aB"
MAINNET_WETH = "0xC02aaA39b223FE8D0A0e5C4F27eAD9083C756Cc2"
SOLVER = "0xe8599F3cc5D38a9aD6F3684cd5CEa72f10Dbc383"
OTHER_SOLVER = "0xDe786877a10DBb7EBa25a4DA65aEcf47654F08ab"
PROTOCOL_FEE_SAFE = "0x22af3D38E50ddedeb7C47f36faB321eC3Bb72A76"
PARTNER = "0x0A61B9F341a3ec8a8112D7dD6FBBC62B7FDF437e"

# Provenance is an input of the builder; these values only satisfy the schema.
PROVENANCE = PlanProvenance(
    run_id="2026-10-13-mainnet-1",
    network="mainnet",
    accounting_period="2026-10-06-to-2026-10-13",
    generator_commit="0123456789abcdef0123456789abcdef01234567",
    config_hash="0x" + "ab" * 32,
)
# PROVENANCE as plan document members.
PROVENANCE_MEMBERS = {
    "runId": "2026-10-13-mainnet-1",
    "network": "mainnet",
    "accountingPeriod": "2026-10-06-to-2026-10-13",
    "generatorCommit": "0123456789abcdef0123456789abcdef01234567",
    "configHash": "0x" + "ab" * 32,
}

# Network names and wrapped native tokens (src/config.py) of the fixture chains.
NETWORKS = {1: "mainnet", 42161: "arbitrum", 59144: "linea"}
WRAPPED_NATIVE_TOKENS = {
    1: "0xc02aaa39b223fe8d0a0e5c4f27ead9083c756cc2",
    42161: "0x82af49447d8a07e3bd95bd0d56f35241523fbab1",
    59144: "0xe5d7c2a44ffddf6b295a15c148167daaaf5cf34f",
}


def native(recipient: str, amount: int) -> Transfer:
    return Transfer(token=None, recipient=Address(recipient), amount_wei=amount)


def erc20(token: str, recipient: str, amount: int) -> Transfer:
    # Token(address) without decimals would ask a node for them.
    return Transfer(
        token=Token(token, 18), recipient=Address(recipient), amount_wei=amount
    )


def native_payout() -> list[Transfer]:
    return [
        native(SOLVER, 3 * 10**17),
        erc20(MAINNET_WETH, PROTOCOL_FEE_SAFE, 5 * 10**16),
        native(OTHER_SOLVER, 2 * 10**17),
        erc20(MAINNET_WETH, PARTNER, 10**16),
    ]


def native_plan(transfers: list[Transfer], balance: int) -> BuiltPlan:
    return multisend_plan(
        chain_id=1,
        safe=MAINNET_SAFE,
        nonce=1466,
        calls=native_multisend_calls(
            transfers, native_balance=balance, wrapped_native_token=MAINNET_WETH
        ),
        provenance=PROVENANCE,
    )


def plan_builders(provenance: PlanProvenance) -> list:
    """Builders of a MultiSend plan and of an empty transaction plan."""
    return [
        lambda: multisend_plan(
            chain_id=1,
            safe=MAINNET_SAFE,
            nonce=1466,
            calls=(NativeTransfer(SOLVER, 1),),
            provenance=provenance,
        ),
        lambda: empty_transaction_plan(
            chain_id=1, safe=MAINNET_SAFE, nonce=1465, provenance=provenance
        ),
    ]


class TestMultisendPlan(unittest.TestCase):
    def test_document(self):
        built = multisend_plan(
            chain_id=1,
            safe=MAINNET_SAFE,
            nonce=1466,
            calls=(
                WrappedNativeWithdrawal(MAINNET_WETH, 7),
                NativeTransfer(SOLVER, 5),
                Erc20Transfer(MAINNET_WETH, PARTNER, 3),
            ),
            provenance=PROVENANCE,
        )
        body = {
            "schemaVersion": 1,
            **PROVENANCE_MEMBERS,
            "chainId": 1,
            "safe": MAINNET_SAFE,
            "nonce": 1466,
            "to": MULTISEND_CALL_ONLY,
            "operation": 1,
            "calls": [
                {
                    "callType": "wrappedNativeWithdrawal",
                    "token": MAINNET_WETH,
                    "amountAtoms": "7",
                },
                {"callType": "nativeTransfer", "recipient": SOLVER, "amountAtoms": "5"},
                {
                    "callType": "erc20Transfer",
                    "token": MAINNET_WETH,
                    "recipient": PARTNER,
                    "amountAtoms": "3",
                },
            ],
        }
        self.assertEqual(built.document, {**body, "planHash": plan_hash(body)})

    def test_identical_calls_are_kept(self):
        """Identical calls are separate payouts: the document, the loaded plan
        and the call count keep every one of them."""
        calls = (
            WrappedNativeWithdrawal(MAINNET_WETH, 10),
            NativeTransfer(SOLVER, 5),
            Erc20Transfer(MAINNET_WETH, PARTNER, 7),
            Erc20Transfer(MAINNET_WETH, PARTNER, 7),
            NativeTransfer(SOLVER, 5),
        )
        built = multisend_plan(
            chain_id=1,
            safe=MAINNET_SAFE,
            nonce=1466,
            calls=calls,
            provenance=PROVENANCE,
        )
        native_call = {
            "callType": "nativeTransfer",
            "recipient": SOLVER,
            "amountAtoms": "5",
        }
        weth_call = {
            "callType": "erc20Transfer",
            "token": MAINNET_WETH,
            "recipient": PARTNER,
            "amountAtoms": "7",
        }
        withdrawal = {
            "callType": "wrappedNativeWithdrawal",
            "token": MAINNET_WETH,
            "amountAtoms": "10",
        }
        self.assertEqual(
            built.document["calls"],
            [withdrawal, native_call, weth_call, weth_call, native_call],
        )
        self.assertEqual(built.plan.calls, calls)
        self.assertEqual(parse_payout_plan(json.dumps(built.document)), built.plan)
        self.assertEqual(len(built.plan.calls), 5)

    def test_round_trip_through_the_loader(self):
        built = native_plan(native_payout(), 10**17)
        self.assertEqual(payout_plan_from_document(built.document), built.plan)
        for text in (
            json.dumps(built.document),
            json.dumps(built.document, indent=2, sort_keys=True),
        ):
            self.assertEqual(parse_payout_plan(text), built.plan)
        plan = built.plan
        self.assertEqual(
            (plan.schema_version, plan.chain_id, plan.safe, plan.nonce),
            (1, 1, MAINNET_SAFE, 1466),
        )
        self.assertEqual(
            plan.calls,
            (WrappedNativeWithdrawal(MAINNET_WETH, 4 * 10**17),)
            + transfer_calls(native_payout()),
        )
        self.assertEqual(plan.plan_hash, built.document["planHash"])

    def test_target_is_the_multisend_call_only_post_multisend_uses(self):
        plan = native_plan(native_payout(), 0).plan
        self.assertEqual((plan.to, plan.operation), (MULTISEND_CALL_ONLY, 1))
        self.assertIn(plan.to, APPROVED_MULTISEND_CONTRACTS)

    def test_addresses_are_written_checksummed(self):
        """Any spelling of the same plan gives the same document and planHash."""

        def build(spell):
            return multisend_plan(
                chain_id=1,
                safe=spell(MAINNET_SAFE),
                nonce=1466,
                calls=(
                    WrappedNativeWithdrawal(spell(MAINNET_WETH), 7),
                    NativeTransfer(spell(SOLVER), 5),
                    Erc20Transfer(spell(MAINNET_WETH), spell(PARTNER), 3),
                ),
                provenance=PROVENANCE,
            ).document

        def build_empty(spell):
            return empty_transaction_plan(
                chain_id=1, safe=spell(MAINNET_SAFE), nonce=1465, provenance=PROVENANCE
            ).document

        for builder in (build, build_empty):
            checksummed = builder(lambda address: address)
            self.assertEqual(builder(str.lower), checksummed)
            self.assertEqual(checksummed["safe"], MAINNET_SAFE)

    def test_invalid_addresses(self):
        typo = "0xA03Be496e67Ec29bC62F01a428683D7F9c204930"
        self.assertFalse(is_checksum_address(typo))
        for build in (
            lambda: empty_transaction_plan(
                chain_id=1, safe=typo, nonce=1465, provenance=PROVENANCE
            ),
            lambda: multisend_plan(
                chain_id=1,
                safe=typo,
                nonce=1466,
                calls=(NativeTransfer(SOLVER, 1),),
                provenance=PROVENANCE,
            ),
        ):
            with self.assertRaisesRegex(ValueError, "safe"):
                build()
        for calls, member in (
            ((NativeTransfer(SOLVER, 1), NativeTransfer(typo, 2)), r"calls\[1\]"),
            ((Erc20Transfer(typo, SOLVER, 2),), r"calls\[0\]\.token"),
            ((Erc20Transfer(COW, typo, 2),), r"calls\[0\]\.recipient"),
            ((WrappedNativeWithdrawal(typo, 2),), r"calls\[0\]\.token"),
        ):
            with self.subTest(member):
                with self.assertRaisesRegex(ValueError, member):
                    multisend_plan(
                        chain_id=1,
                        safe=MAINNET_SAFE,
                        nonce=1466,
                        calls=calls,
                        provenance=PROVENANCE,
                    )

    def test_empty_transfer_list_is_rejected(self):
        """post_multisend proposes nothing for an empty list, so there is no
        MultiSend to plan, and the loader rejects a DELEGATECALL plan without
        calls."""
        for calls in (
            cow_multisend_calls([]),
            native_multisend_calls(
                [], native_balance=0, wrapped_native_token=MAINNET_WETH
            ),
        ):
            with self.assertRaisesRegex(
                PayoutPlanError,
                "calls: a MultiSend transaction needs at least one call",
            ):
                multisend_plan(
                    chain_id=1,
                    safe=MAINNET_SAFE,
                    nonce=1466,
                    calls=calls,
                    provenance=PROVENANCE,
                )


class TestEmptyTransactionPlan(unittest.TestCase):
    def test_document(self):
        built = empty_transaction_plan(
            chain_id=1, safe=MAINNET_SAFE, nonce=1465, provenance=PROVENANCE
        )
        body = {
            "schemaVersion": 1,
            **PROVENANCE_MEMBERS,
            "chainId": 1,
            "safe": MAINNET_SAFE,
            "nonce": 1465,
            "to": MAINNET_SAFE,
            "operation": 0,
            "calls": [],
        }
        self.assertEqual(built.document, {**body, "planHash": plan_hash(body)})
        self.assertEqual(
            (built.plan.to, built.plan.operation, built.plan.calls),
            (MAINNET_SAFE, 0, ()),
        )
        self.assertEqual(parse_payout_plan(json.dumps(built.document)), built.plan)


class TestPlanHash(unittest.TestCase):
    def test_deterministic(self):
        first = native_plan(native_payout(), 10**17)
        second = native_plan(native_payout(), 10**17)
        self.assertEqual(first.document, second.document)
        self.assertEqual(first.plan, second.plan)
        self.assertEqual(first.document["planHash"], plan_hash(first.document))

    def test_canonical_serialisation(self):
        document = native_plan(native_payout(), 10**17).document
        body = {key: value for key, value in document.items() if key != "planHash"}
        canonical = json.dumps(body, sort_keys=True, separators=(",", ":"))
        self.assertEqual(
            document["planHash"],
            "0x" + hashlib.sha256(canonical.encode("ascii")).hexdigest(),
        )

    def test_one_atom_changes_the_hash(self):
        honest = native_plan(native_payout(), 10**17)
        changes = {}
        for index in range(len(native_payout())):
            transfers = native_payout()
            transfers[index].amount_wei += 1
            changes[f"transfer {index}"] = native_plan(transfers, 10**17)
        changes["balance"] = native_plan(native_payout(), 10**17 - 1)
        for label, changed in changes.items():
            with self.subTest(label):
                self.assertNotEqual(
                    changed.document["planHash"], honest.document["planHash"]
                )
                self.assertNotEqual(changed.plan.calls, honest.plan.calls)


class TestProvenance(unittest.TestCase):
    def test_provenance_is_copied_unchanged(self):
        for build in plan_builders(PROVENANCE):
            plan = build().plan
            self.assertEqual(
                (
                    plan.run_id,
                    plan.network,
                    plan.accounting_period,
                    plan.generator_commit,
                    plan.config_hash,
                ),
                dataclasses.astuple(PROVENANCE),
            )

    def test_provenance_is_validated_by_the_loader(self):
        for field, value, member in (
            ("run_id", "", "runId"),
            ("run_id", "run id with spaces", "runId"),
            ("network", "Mainnet", "network"),
            ("accounting_period", "2026-10-13", "accountingPeriod"),
            ("accounting_period", "2026-10-13-to-2026-10-06", "accountingPeriod"),
            ("generator_commit", "13b3671", "generatorCommit"),
            ("config_hash", "ab" * 32, "configHash"),
        ):
            provenance = dataclasses.replace(PROVENANCE, **{field: value})
            for build in plan_builders(provenance):
                with self.subTest(field=field, value=value):
                    with self.assertRaisesRegex(PayoutPlanError, member):
                        build()

    def test_identity_is_validated_by_the_loader(self):
        for changes, member in (
            ({"chain_id": 0}, "chainId"),
            ({"chain_id": True}, "chainId"),
            ({"nonce": -1}, "nonce"),
            ({"nonce": "1466"}, "nonce"),
        ):
            arguments = {
                "chain_id": 1,
                "safe": MAINNET_SAFE,
                "nonce": 1465,
                "provenance": PROVENANCE,
                **changes,
            }
            with self.subTest(changes):
                with self.assertRaisesRegex(PayoutPlanError, member):
                    empty_transaction_plan(**arguments)
                with self.assertRaisesRegex(PayoutPlanError, member):
                    multisend_plan(calls=(NativeTransfer(SOLVER, 1),), **arguments)


def equivalent_transfers(recorded: RecordedTransaction) -> tuple[list[Transfer], int]:
    """Transfer objects equivalent to a recorded payout's transfer calls and
    the amount of its withdrawal (0 if it has none), from the Safe Transaction
    Service's decoding of it."""
    transfers, withdrawal = [], 0
    for call in planned_calls(recorded):
        amount = int(call["amountAtoms"])
        if call["callType"] == "nativeTransfer":
            transfers.append(native(call["recipient"], amount))
        elif call["callType"] == "erc20Transfer":
            transfers.append(erc20(call["token"], call["recipient"], amount))
        else:
            withdrawal = amount
    return transfers, withdrawal


def plan_from_equivalent_transfers(recorded: RecordedTransaction) -> BuiltPlan:
    transaction = recorded.transaction
    identity = {
        "chain_id": transaction.chain_id,
        "safe": transaction.safe,
        "nonce": transaction.nonce,
        "provenance": dataclasses.replace(
            PROVENANCE, network=NETWORKS[transaction.chain_id]
        ),
    }
    if transaction.operation == 0:
        return empty_transaction_plan(**identity)
    transfers, withdrawal = equivalent_transfers(recorded)
    native_total = sum(t.amount_wei for t in transfers if t.token is None)
    if native_total == 0:
        calls = cow_multisend_calls(transfers)
    else:
        # The balance at which the unwrap rule reproduces the recorded withdrawal.
        calls = native_multisend_calls(
            transfers,
            native_balance=native_total - withdrawal,
            wrapped_native_token=WRAPPED_NATIVE_TOKENS[transaction.chain_id],
        )
    return multisend_plan(calls=calls, **identity)


class TestFormatCompatibilityWithRecordedPayouts(unittest.TestCase):
    """Plans built from Transfer objects equivalent to recorded payout
    transactions verify against those transactions.

    This checks that built plans fit real payouts: identity, MultiSend target,
    call types, address spelling and call order, on Safe v1.3.0 and v1.4.1.
    It is a format-compatibility check, not a same-run check: the transfers
    and balances are derived from each recorded transaction.
    """

    def test_mainnet_native_payout_with_unwrap_and_wrapped_native_transfers(self):
        """Mainnet nonce 1466: a WETH withdrawal, then 65 native transfers and
        3 WETH transfers in one native MultiSend."""
        recorded = load(MAINNET_NATIVE)
        transfers, withdrawal = equivalent_transfers(recorded)
        # The withdrawal equals the sum of the native transfers, so a native
        # balance of 0 reproduces it.
        self.assertEqual(
            withdrawal, sum(t.amount_wei for t in transfers if t.token is None)
        )
        built = multisend_plan(
            chain_id=1,
            safe=MAINNET_SAFE,
            nonce=1466,
            calls=native_multisend_calls(
                transfers, native_balance=0, wrapped_native_token=MAINNET_WETH
            ),
            provenance=PROVENANCE,
        )
        report = verify_safe_transaction(
            built.plan,
            recorded.transaction,
            reported_safe_tx_hash=recorded.reported_safe_tx_hash,
        )
        self.assertEqual(report.failures, ())
        self.assertEqual(report.calls, built.plan.calls)
        self.assertEqual(
            built.plan.calls[0],
            WrappedNativeWithdrawal(MAINNET_WETH, 60467858369429154823),
        )
        self.assertEqual(
            Counter(type(call) for call in built.plan.calls),
            {WrappedNativeWithdrawal: 1, NativeTransfer: 65, Erc20Transfer: 3},
        )
        self.assertEqual(
            {
                call.token
                for call in built.plan.calls
                if isinstance(call, Erc20Transfer)
            },
            {MAINNET_WETH},
        )

    def test_every_plannable_fixture(self):
        for name in PLANNABLE_FIXTURES:
            with self.subTest(name):
                recorded = load(name)
                built = plan_from_equivalent_transfers(recorded)
                report = verify_safe_transaction(
                    built.plan,
                    recorded.transaction,
                    reported_safe_tx_hash=recorded.reported_safe_tx_hash,
                )
                self.assertEqual(report.failures, ())
                self.assertEqual(report.calls, built.plan.calls)
                self.assertEqual(len(built.plan.calls), len(recorded.inner))


class EncoderCalled(Exception):
    """Raised by the patched Transfer.as_multisend_tx."""


class TestIndependenceFromTheTransaction(unittest.TestCase):
    """The plan is built from the payout intent and never from the transaction
    CoW's code encodes from it."""

    def test_plans_build_while_as_multisend_tx_raises(self):
        cow = [erc20(COW, SOLVER, 10**21), erc20(COW, OTHER_SOLVER, 2 * 10**21)]
        payout = native_payout()
        with mock.patch.object(
            Transfer, "as_multisend_tx", autospec=True, side_effect=EncoderCalled
        ) as encoder:
            with self.assertRaises(EncoderCalled):
                payout[0].as_multisend_tx()
            unwrap = expected_unwrap(
                payout, native_balance=10**17, wrapped_native_token=MAINNET_WETH
            )
            cow_built = multisend_plan(
                chain_id=1,
                safe=MAINNET_SAFE,
                nonce=1464,
                calls=cow_multisend_calls(cow),
                provenance=PROVENANCE,
            )
            empty_built = empty_transaction_plan(
                chain_id=1, safe=MAINNET_SAFE, nonce=1465, provenance=PROVENANCE
            )
            native_built = native_plan(payout, 10**17)
        # Called once, by the check above that the patch is in effect.
        self.assertEqual(encoder.call_count, 1)
        self.assertEqual(unwrap, WrappedNativeWithdrawal(MAINNET_WETH, 4 * 10**17))
        self.assertEqual(
            cow_built.plan.calls,
            (
                Erc20Transfer(COW, SOLVER, 10**21),
                Erc20Transfer(COW, OTHER_SOLVER, 2 * 10**21),
            ),
        )
        self.assertEqual(
            (empty_built.plan.to, empty_built.plan.operation), (MAINNET_SAFE, 0)
        )
        self.assertEqual(
            native_built.plan.calls,
            (
                unwrap,
                NativeTransfer(SOLVER, 3 * 10**17),
                Erc20Transfer(MAINNET_WETH, PROTOCOL_FEE_SAFE, 5 * 10**16),
                NativeTransfer(OTHER_SOLVER, 2 * 10**17),
                Erc20Transfer(MAINNET_WETH, PARTNER, 10**16),
            ),
        )

    def test_plan_modules_do_not_load_the_encoders(self):
        """Importing the plan modules loads neither src.multisend, safe-eth-py
        and web3 nor CoW's Transfer and Token modules, which load them, and
        needs no configuration."""
        root = Path(__file__).parent.parent.parent
        code = (
            "import sys\n"
            "import src.verification.expected_calls\n"
            "import src.verification.plan_builder\n"
            "loaded = set(sys.modules) | {name.split('.')[0] for name in sys.modules}\n"
            "print(sorted(loaded & {'safe_eth', 'web3', 'src.multisend',\n"
            "    'src.models.transfer', 'src.models.token', 'src.config'}))\n"
        )
        result = subprocess.run(
            [sys.executable, "-c", code],
            cwd=root,
            env={"PATH": os.environ.get("PATH", "")},
            capture_output=True,
            text=True,
            check=False,
        )
        self.assertEqual(result.returncode, 0, result.stderr)
        self.assertEqual(result.stdout.strip(), "[]")


if __name__ == "__main__":
    unittest.main()
