"""Tests for src/verification/strict_verifier.py.

Honest recorded payouts must pass. Every mutation below must fail, and must be
caught by the check it targets rather than incidentally.
"""

from __future__ import annotations

import copy
import dataclasses
import json
import os
import subprocess
import sys
import unittest
from collections import Counter
from collections.abc import Callable
from pathlib import Path

import pytest
from eth_utils.crypto import keccak
from safe_eth.safe.multi_send import MultiSendOperation, MultiSendTx
from web3 import Web3

from src.verification.calldata import ERC20_TRANSFER_SELECTOR, NativeTransfer
from src.verification.payout_plan import PayoutPlan, parse_payout_plan
from src.verification.safe_transaction import SafeTransaction
from src.verification.strict_verifier import (
    VerificationReport,
    verify_safe_transaction,
)
from tests.unit.safe_transaction_fixtures import (
    ARBITRUM_NATIVE,
    ARBITRUM_NATIVE_SUPERSEDED,
    ARBITRUM_OVERDRAFTS,
    LINEA_EMPTY,
    LINEA_NATIVE,
    MAINNET_COW,
    PLANNABLE_FIXTURES,
    load,
    multisend_txs,
    plan_document,
    plan_for,
    producer_encoding,
    with_plan_hash,
)

ATTACKER = Web3.to_checksum_address("0x" + "ba5e" * 10)
ZERO_ADDRESS = "0x" + "0" * 40
COW = Web3.to_checksum_address("0xdef1ca1fb7fbcdc777520aa7f396b4e015f497ab")
MAINNET_WETH = Web3.to_checksum_address("0xc02aaa39b223fe8d0a0e5c4f27ead9083c756cc2")
# MultiSendCallOnly v1.4.1: a genuine Safe contract, but not the one the
# payout script uses.
MULTISEND_CALL_ONLY_V141 = "0x9641d764fc13c8B624c04430C7356C1C7C8102e2"


@dataclasses.dataclass(frozen=True)
class Case:
    """A plan and a transaction to verify against it."""

    plan: PayoutPlan
    transaction: SafeTransaction
    reported_safe_tx_hash: bytes | None

    def verify(self) -> VerificationReport:
        return verify_safe_transaction(
            self.plan,
            self.transaction,
            reported_safe_tx_hash=self.reported_safe_tx_hash,
        )


Edit = Callable[[list[MultiSendTx]], list[MultiSendTx]]
Transform = Callable[[SafeTransaction], SafeTransaction]


def tampered(
    name: str, edit: Edit | None = None, transform: Transform | None = None
) -> Case:
    """The honest plan against a tampered transaction.

    The transaction's MultiSend is rebuilt from an edited MultiSendTx list the
    way the payout script builds it. The reported safeTxHash is the tampered
    transaction's own, as the Safe Transaction Service would show it.
    """
    recorded = load(name)
    transaction = recorded.transaction
    if edit is not None:
        data = producer_encoding(edit(multisend_txs(recorded)))
        transaction = dataclasses.replace(transaction, data=data)
    if transform is not None:
        transaction = transform(transaction)
    return Case(plan_for(recorded), transaction, transaction.safe_tx_hash())


def misplanned(name: str, edit: Callable[[dict], None]) -> Case:
    """A wrong plan against the honest transaction."""
    recorded = load(name)
    document = copy.deepcopy(plan_document(recorded))
    edit(document)
    plan = parse_payout_plan(json.dumps(with_plan_hash(document)))
    return Case(plan, recorded.transaction, recorded.reported_safe_tx_hash)


def replace(**changes) -> Transform:
    return lambda transaction: dataclasses.replace(transaction, **changes)


def erc20_transfer(token: str, recipient: str, amount: int) -> MultiSendTx:
    data = (
        ERC20_TRANSFER_SELECTOR
        + bytes(12)
        + bytes.fromhex(recipient[2:])
        + amount.to_bytes(32, "big")
    )
    return MultiSendTx(MultiSendOperation.CALL, token, 0, data)


def with_amount(transaction: MultiSendTx, delta: int) -> MultiSendTx:
    """The same call with its amount (last word, or native value) changed."""
    data = bytes(transaction.data)
    if not data:
        return MultiSendTx(
            transaction.operation, transaction.to, transaction.value + delta, b""
        )
    amount = int.from_bytes(data[-32:], "big") + delta
    return MultiSendTx(
        transaction.operation,
        transaction.to,
        transaction.value,
        data[:-32] + amount.to_bytes(32, "big"),
    )


def with_recipient(transaction: MultiSendTx, recipient: str) -> MultiSendTx:
    data = bytes(transaction.data)
    return MultiSendTx(
        transaction.operation,
        transaction.to,
        transaction.value,
        data[:16] + bytes.fromhex(recipient[2:]) + data[36:],
    )


def with_fields(transaction: MultiSendTx, **changes) -> MultiSendTx:
    fields = {
        "operation": transaction.operation,
        "to": transaction.to,
        "value": transaction.value,
        "data": bytes(transaction.data),
        **changes,
    }
    return MultiSendTx(**fields)


def old_plan_for_new_run() -> Case:
    """The plan of the payout run that proposed the superseded nonce 213
    transaction, paired with the transaction a later run proposed and the
    Safe executed at the same nonce."""
    new_run = load(ARBITRUM_NATIVE)
    return Case(
        plan_for(load(ARBITRUM_NATIVE_SUPERSEDED)),
        new_run.transaction,
        new_run.reported_safe_tx_hash,
    )


def new_plan_for_old_run() -> Case:
    old_run = load(ARBITRUM_NATIVE_SUPERSEDED)
    return Case(
        plan_for(load(ARBITRUM_NATIVE)),
        old_run.transaction,
        old_run.reported_safe_tx_hash,
    )


def overdrafts_against_payout_plan() -> Case:
    """Overdraft transactions are not covered; they must not pass either."""
    recorded = load(ARBITRUM_OVERDRAFTS)
    document = plan_document(load(ARBITRUM_NATIVE))
    document["nonce"] = recorded.transaction.nonce
    plan = parse_payout_plan(json.dumps(with_plan_hash(document)))
    return Case(plan, recorded.transaction, recorded.reported_safe_tx_hash)


def unapproved_target_everywhere() -> Case:
    """Plan and transaction agree on a target that is not MultiSendCallOnly."""
    case = misplanned(MAINNET_COW, lambda document: document.update(to=ATTACKER))
    transaction = dataclasses.replace(case.transaction, to=ATTACKER)
    return Case(case.plan, transaction, transaction.safe_tx_hash())


def original_hash_for_tampered_calldata() -> Case:
    honest = load(MAINNET_COW)
    case = tampered(MAINNET_COW, lambda txs: [with_amount(txs[0], 1)] + txs[1:])
    return dataclasses.replace(case, reported_safe_tx_hash=honest.reported_safe_tx_hash)


def gas_price_refund_to_executor() -> Case:
    """Only gasPrice is set. That alone makes the Safe refund execution gas,
    and with refundReceiver left at the zero address the refund goes to
    tx.origin, whoever executes (handlePayment in GnosisSafe.sol v1.3.0 and
    Safe.sol v1.4.1)."""
    case = tampered(MAINNET_COW, transform=replace(gas_price=10**9))
    assert case.transaction.refund_receiver == ZERO_ADDRESS
    return case


APPROVE = keccak(text="approve(address,uint256)")[:4]

# (mutation, case builder, what must be reported). Each expected entry is how
# a failure message starts: a category such as "missing", or something more
# specific such as "gas refund: gasPrice".
MUTATIONS: list[tuple[str, Callable[[], Case], set[str]]] = [
    # --- amounts ---
    (
        "one-atom increase",
        lambda: tampered(MAINNET_COW, lambda txs: [with_amount(txs[0], 1)] + txs[1:]),
        {"missing", "unexpected"},
    ),
    (
        "one-atom decrease",
        lambda: tampered(
            MAINNET_COW, lambda txs: txs[:30] + [with_amount(txs[30], -1)]
        ),
        {"missing", "unexpected"},
    ),
    (
        "change hidden by 10-significant-digit display (+1e11 atoms)",
        lambda: tampered(
            MAINNET_COW, lambda txs: [with_amount(txs[0], 10**11)] + txs[1:]
        ),
        {"missing", "unexpected"},
    ),
    (
        "one-wei native increase",
        lambda: tampered(
            ARBITRUM_NATIVE, lambda txs: txs[:5] + [with_amount(txs[5], 1)] + txs[6:]
        ),
        {"missing", "unexpected"},
    ),
    # --- extra, missing, duplicated calls ---
    (
        "additional 5000 COW transfer to an arbitrary address",
        lambda: tampered(
            MAINNET_COW,
            lambda txs: txs + [erc20_transfer(COW, ATTACKER, 5000 * 10**18)],
        ),
        {"unexpected"},
    ),
    (
        "additional native transfer to an arbitrary address",
        lambda: tampered(
            ARBITRUM_NATIVE,
            lambda txs: txs
            + [MultiSendTx(MultiSendOperation.CALL, ATTACKER, 10**18, b"")],
        ),
        {"unexpected"},
    ),
    (
        "missing ERC-20 transfer",
        lambda: tampered(MAINNET_COW, lambda txs: txs[:4] + txs[5:]),
        {"missing"},
    ),
    (
        "duplicated ERC-20 transfer",
        lambda: tampered(MAINNET_COW, lambda txs: txs[:1] + txs[:1] + txs[1:]),
        {"unexpected"},
    ),
    (
        "omitted native-value call",
        lambda: tampered(ARBITRUM_NATIVE, lambda txs: txs[:-1]),
        {"missing"},
    ),
    (
        "omitted native-value call (Safe v1.4.1, no unwrap)",
        lambda: tampered(LINEA_NATIVE, lambda txs: txs[1:]),
        {"missing"},
    ),
    (
        "duplicated native-value call",
        lambda: tampered(ARBITRUM_NATIVE, lambda txs: txs + txs[-1:]),
        {"unexpected"},
    ),
    # --- recipients and tokens ---
    (
        "wrong recipient",
        lambda: tampered(
            MAINNET_COW, lambda txs: [with_recipient(txs[0], ATTACKER)] + txs[1:]
        ),
        {"missing", "unexpected"},
    ),
    (
        "wrong native recipient",
        lambda: tampered(
            ARBITRUM_NATIVE, lambda txs: txs[:-1] + [with_fields(txs[-1], to=ATTACKER)]
        ),
        {"missing", "unexpected"},
    ),
    (
        "wrong token",
        lambda: tampered(
            MAINNET_COW, lambda txs: [with_fields(txs[0], to=MAINNET_WETH)] + txs[1:]
        ),
        {"missing", "unexpected"},
    ),
    # --- transaction identity ---
    (
        "wrong Safe",
        lambda: tampered(MAINNET_COW, transform=replace(safe=ATTACKER)),
        {"Safe"},
    ),
    (
        "wrong nonce",
        lambda: tampered(
            MAINNET_COW,
            transform=lambda tx: dataclasses.replace(tx, nonce=tx.nonce + 1),
        ),
        {"nonce"},
    ),
    (
        "wrong chain ID",
        lambda: tampered(MAINNET_COW, transform=replace(chain_id=42161)),
        {"chain id"},
    ),
    (
        "wrong MultiSend target",
        lambda: tampered(MAINNET_COW, transform=replace(to=MULTISEND_CALL_ONLY_V141)),
        {"target"},
    ),
    (
        "unapproved target in both plan and transaction",
        unapproved_target_everywhere,
        {"target"},
    ),
    (
        "wrong operation (CALL instead of DELEGATECALL)",
        lambda: tampered(MAINNET_COW, transform=replace(operation=0)),
        {"operation"},
    ),
    (
        "outer transaction sends value",
        lambda: tampered(MAINNET_COW, transform=replace(value=1)),
        {"value"},
    ),
    (
        "gas refund paid to an arbitrary receiver",
        lambda: tampered(
            MAINNET_COW,
            transform=replace(
                safe_tx_gas=100000, gas_price=10**9, refund_receiver=ATTACKER
            ),
        ),
        {"gas refund"},
    ),
    (
        "gas refund paid in a token",
        lambda: tampered(ARBITRUM_NATIVE, transform=replace(base_gas=1, gas_token=COW)),
        {"gas refund"},
    ),
    # One field at a time, so that every gas refund check must fire on its own.
    (
        "gas refund: safeTxGas alone",
        lambda: tampered(MAINNET_COW, transform=replace(safe_tx_gas=100000)),
        {"gas refund: safeTxGas"},
    ),
    (
        "gas refund: baseGas alone",
        lambda: tampered(MAINNET_COW, transform=replace(base_gas=50000)),
        {"gas refund: baseGas"},
    ),
    (
        "gas refund: gasPrice alone, refunding tx.origin",
        gas_price_refund_to_executor,
        {"gas refund: gasPrice"},
    ),
    (
        "gas refund: gasToken alone",
        lambda: tampered(MAINNET_COW, transform=replace(gas_token=COW)),
        {"gas refund: gasToken"},
    ),
    (
        "gas refund: refundReceiver alone",
        lambda: tampered(MAINNET_COW, transform=replace(refund_receiver=ATTACKER)),
        {"gas refund: refundReceiver"},
    ),
    (
        "reported safeTxHash differs from the transaction",
        original_hash_for_tampered_calldata,
        {"safeTxHash", "missing", "unexpected"},
    ),
    # --- WETH withdrawal ---
    (
        "malformed WETH withdrawal: truncated calldata",
        lambda: tampered(
            ARBITRUM_NATIVE,
            lambda txs: [with_fields(txs[0], data=bytes(txs[0].data)[:-1])] + txs[1:],
        ),
        {"calldata"},
    ),
    (
        "malformed WETH withdrawal: over-long calldata",
        lambda: tampered(
            ARBITRUM_NATIVE,
            lambda txs: [with_fields(txs[0], data=bytes(txs[0].data) + b"\x00")]
            + txs[1:],
        ),
        {"calldata"},
    ),
    (
        "malformed WETH withdrawal: carries native value",
        lambda: tampered(
            ARBITRUM_NATIVE, lambda txs: [with_fields(txs[0], value=1)] + txs[1:]
        ),
        {"calldata"},
    ),
    (
        "malformed WETH withdrawal: amount off by one",
        lambda: tampered(
            ARBITRUM_NATIVE, lambda txs: [with_amount(txs[0], 1)] + txs[1:]
        ),
        {"missing", "unexpected"},
    ),
    (
        "malformed WETH withdrawal: called on another contract",
        lambda: tampered(
            ARBITRUM_NATIVE, lambda txs: [with_fields(txs[0], to=ATTACKER)] + txs[1:]
        ),
        {"missing", "unexpected"},
    ),
    (
        "WETH withdrawal after the native transfers",
        lambda: tampered(ARBITRUM_NATIVE, lambda txs: txs[1:] + txs[:1]),
        {"ordering"},
    ),
    (
        "WETH withdrawal duplicated",
        lambda: tampered(ARBITRUM_NATIVE, lambda txs: txs[:1] + txs),
        {"ordering", "unexpected"},
    ),
    (
        "WETH withdrawal omitted",
        lambda: tampered(ARBITRUM_NATIVE, lambda txs: txs[1:]),
        {"missing"},
    ),
    # --- calls the payout script never produces ---
    (
        "unknown selector (approve)",
        lambda: tampered(
            MAINNET_COW,
            lambda txs: txs
            + [
                with_fields(
                    txs[0],
                    data=APPROVE
                    + bytes(12)
                    + bytes.fromhex(ATTACKER[2:])
                    + b"\xff" * 32,
                )
            ],
        ),
        {"calldata"},
    ),
    (
        "inner DELEGATECALL",
        lambda: tampered(
            MAINNET_COW,
            lambda txs: [
                with_fields(txs[0], operation=MultiSendOperation.DELEGATE_CALL)
            ]
            + txs[1:],
        ),
        {"calldata"},
    ),
    (
        "dirty address padding",
        lambda: tampered(
            MAINNET_COW,
            lambda txs: [
                with_fields(
                    txs[0],
                    data=bytes(txs[0].data)[:4] + b"\x01" + bytes(txs[0].data)[5:],
                )
            ]
            + txs[1:],
        ),
        {"calldata"},
    ),
    (
        "native value on an ERC-20 transfer",
        lambda: tampered(
            MAINNET_COW, lambda txs: [with_fields(txs[0], value=1)] + txs[1:]
        ),
        {"calldata"},
    ),
    (
        "trailing bytes after the MultiSend payload",
        lambda: tampered(
            MAINNET_COW,
            transform=lambda tx: dataclasses.replace(tx, data=tx.data + bytes(32)),
        ),
        {"calldata"},
    ),
    (
        "truncated MultiSend payload",
        lambda: tampered(
            MAINNET_COW,
            transform=lambda tx: dataclasses.replace(tx, data=tx.data[:-32]),
        ),
        {"calldata"},
    ),
    (
        "overdrafts transaction (not covered) against a payout plan",
        overdrafts_against_payout_plan,
        {"calldata"},
    ),
    # --- empty nonce-reservation transaction ---
    (
        "empty transaction carrying calldata",
        lambda: tampered(LINEA_EMPTY, transform=replace(data=b"\x00")),
        {"empty transaction"},
    ),
    (
        "empty transaction calling another address",
        lambda: tampered(LINEA_EMPTY, transform=replace(to=ATTACKER)),
        {"target", "empty transaction"},
    ),
    (
        "empty transaction as DELEGATECALL",
        lambda: tampered(LINEA_EMPTY, transform=replace(operation=1)),
        {"operation"},
    ),
    (
        "empty transaction sending value",
        lambda: tampered(LINEA_EMPTY, transform=replace(value=1)),
        {"value"},
    ),
    # --- wrong plans ---
    (
        "plan one atom off",
        lambda: misplanned(
            MAINNET_COW,
            lambda d: d["calls"][3].update(
                amountAtoms=str(int(d["calls"][3]["amountAtoms"]) + 1)
            ),
        ),
        {"missing", "unexpected"},
    ),
    (
        "plan omits a call the transaction makes",
        lambda: misplanned(ARBITRUM_NATIVE, lambda d: d["calls"].pop(7)),
        {"unexpected"},
    ),
    (
        "old plan paired with a new run's transaction",
        old_plan_for_new_run,
        {"missing", "unexpected"},
    ),
    (
        "new plan paired with an old run's transaction",
        new_plan_for_old_run,
        {"missing", "unexpected"},
    ),
]


def reported(report: VerificationReport, start: str) -> bool:
    """Whether a failure message starts with ``start``.

    A category ("missing") must be the whole category of the message. A longer
    start ("gas refund: gasPrice") must end at a word, so it does not match
    "gas refund: gasPriceX ...".
    """
    boundary = " " if ":" in start else ":"
    return any(failure.startswith(start + boundary) for failure in report.failures)


@pytest.mark.parametrize("name", PLANNABLE_FIXTURES)
def test_honest_transaction_passes(name):
    recorded = load(name)
    plan = plan_for(recorded)
    report = verify_safe_transaction(
        plan, recorded.transaction, reported_safe_tx_hash=recorded.reported_safe_tx_hash
    )
    assert report.failures == ()
    assert report.passed
    assert report.safe_tx_hash == recorded.reported_safe_tx_hash
    # every inner call of the transaction is decoded and accounted for
    assert len(report.calls) == len(recorded.inner)
    assert Counter(report.calls) == Counter(plan.calls)
    assert report.summary().startswith("PASS")


@pytest.mark.parametrize(
    "mutation, build, expected",
    MUTATIONS,
    ids=[mutation for mutation, _, _ in MUTATIONS],
)
def test_mutation_fails(mutation, build, expected):
    report = build().verify()
    assert not report.passed, mutation
    assert all(reported(report, start) for start in expected), report.failures
    assert report.summary().startswith("FAIL")


def test_old_plan_new_run_reports_exactly_the_drift():
    """Between the two runs a 682811024374 wei transfer was dropped and the
    unwrap shrank by the same amount."""
    report = old_plan_for_new_run().verify()
    weth = "0x82aF49447D8a07e3bd95BD0d56f35241523fBab1"
    assert report.failures == (
        f"missing: withdrawal of 6435646044438025373 wei from wrapped native token {weth} "
        "(plan expects 1, transaction has 0)",
        "missing: native transfer of 682811024374 wei to "
        "0xe8599F3cc5D38a9aD6F3684cd5CEa72f10Dbc383 (plan expects 1, transaction has 0)",
        f"unexpected: withdrawal of 6435645361627000999 wei from wrapped native token {weth} "
        "(transaction has 1, plan expects 0)",
    )


def test_missing_and_unexpected_are_counted():
    case = tampered(ARBITRUM_NATIVE, lambda txs: txs + txs[-1:] + txs[-1:])
    report = case.verify()
    last = report.calls[-1]
    assert isinstance(last, NativeTransfer)
    assert report.failures == (
        f"unexpected: {last} (transaction has 3, plan expects 1)",
    )


def test_summary_lists_totals():
    recorded = load(ARBITRUM_NATIVE)
    report = verify_safe_transaction(plan_for(recorded), recorded.transaction)
    assert report.summary().splitlines()[1:] == [
        "  withdrawals from 0x82aF49447D8a07e3bd95BD0d56f35241523fBab1 (wei): "
        "1 calls, total 6435645361627000999",
        "  native transfers (wei): 23 calls, total 6754301714459485126",
    ]


def test_report_has_no_warnings():
    """Strict mode cannot pass with warnings: there is nowhere to put one."""
    assert {field.name for field in dataclasses.fields(VerificationReport)} == {
        "plan_hash",
        "safe_tx_hash",
        "calls",
        "failures",
    }


def test_verifier_needs_no_keys_or_configuration():
    """Importing and running the verifier needs no private key, API key or
    environment variables."""
    root = Path(__file__).parent.parent.parent
    code = (
        "from tests.unit.safe_transaction_fixtures import load, plan_for, MAINNET_COW\n"
        "from src.verification.strict_verifier import verify_safe_transaction\n"
        "r = load(MAINNET_COW)\n"
        "assert verify_safe_transaction(plan_for(r), r.transaction).passed\n"
    )
    result = subprocess.run(
        [sys.executable, "-c", code],
        cwd=root,
        env={"PATH": os.environ.get("PATH", "")},
        capture_output=True,
        text=True,
        check=False,
    )
    assert result.returncode == 0, result.stderr


if __name__ == "__main__":
    unittest.main()
