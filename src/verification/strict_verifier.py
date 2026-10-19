"""Strict, atom-exact verification of a Safe transaction against a payout plan.

``verify_safe_transaction`` recomputes the safeTxHash, decodes the calldata
independently (``src.verification.calldata``) and compares the result with the
plan. There is no tolerance and there are no warnings: every finding is a
failure, and the transaction passes only when there are none.

- The chain, Safe, nonce, target and operation must equal the plan's.
- The outer value and every gas refund parameter must be zero, as in every
  transaction ``post_multisend`` and ``post_empty_transaction`` build; a
  non-zero ``gasPrice`` with a ``refundReceiver`` would pay the executor
  from the Safe.
- A MultiSend must DELEGATECALL an approved MultiSendCallOnly contract. Its
  decoded calls must equal the plan's calls as a multiset: each planned call
  occurs in the transaction exactly as often as in the plan, and the
  transaction makes no call the plan does not list. A wrapped native
  withdrawal may occur at most once and only as the first call, where
  ``prepend_unwrap_if_necessary`` inserts it.
- The empty nonce-reservation transaction must CALL the Safe itself without
  calldata.

What is verified is that the transaction is exactly the plan. Whether the
plan's amounts are the right rewards is outside the scope of this check.
"""

from __future__ import annotations

from collections import Counter
from collections.abc import Sequence
from dataclasses import dataclass

from eth_utils.address import to_checksum_address

from src.verification.calldata import (
    DELEGATE_CALL,
    CalldataError,
    Erc20Transfer,
    NativeTransfer,
    PayoutCall,
    WrappedNativeWithdrawal,
    decode_payout_calls,
)
from src.verification.payout_plan import PayoutPlan
from src.verification.safe_transaction import SafeTransaction

# MultiSendCallOnly v1.3.0, the only target post_multisend() uses. The same
# runtime code is deployed at this address on every supported network.
MULTISEND_CALL_ONLY = to_checksum_address("0x40A2aCCbd92BCA938b02010E17A5b8929b49130D")
APPROVED_MULTISEND_CONTRACTS = frozenset({MULTISEND_CALL_ONLY})
ZERO_ADDRESS = to_checksum_address(bytes(20))

_OPERATION_NAMES = {0: "0 (CALL)", 1: "1 (DELEGATECALL)"}


@dataclass(frozen=True)
class VerificationReport:
    """Outcome of verifying one Safe transaction against one payout plan."""

    plan_hash: str
    safe_tx_hash: bytes
    calls: tuple[PayoutCall, ...]
    failures: tuple[str, ...]

    @property
    def passed(self) -> bool:
        """True exactly when nothing failed."""
        return not self.failures

    def summary(self) -> str:
        """Human readable verdict, failures and totals of the decoded calls."""
        if self.passed:
            verdict = "PASS: Safe transaction 0x{} exactly matches payout plan {}"
        else:
            verdict = "FAIL: Safe transaction 0x{} does not match payout plan {}"
        lines = [verdict.format(self.safe_tx_hash.hex(), self.plan_hash)]
        lines += [f"  - {failure}" for failure in self.failures]
        lines += [f"  {line}" for line in _totals(self.calls)]
        return "\n".join(lines)


def verify_safe_transaction(
    plan: PayoutPlan,
    transaction: SafeTransaction,
    *,
    reported_safe_tx_hash: bytes | None = None,
) -> VerificationReport:
    """Verify ``transaction`` against ``plan``.

    ``reported_safe_tx_hash`` is the hash shown to signers, for example by the
    Safe Transaction Service. When given it must equal the recomputed hash.
    """
    safe_tx_hash = transaction.safe_tx_hash()
    failures = _identity_failures(plan, transaction)
    failures += _execution_parameter_failures(transaction)
    if reported_safe_tx_hash is not None and reported_safe_tx_hash != safe_tx_hash:
        failures.append(
            f"safeTxHash: reported 0x{reported_safe_tx_hash.hex()}, "
            f"recomputed 0x{safe_tx_hash.hex()}"
        )
    calls: tuple[PayoutCall, ...] = ()
    if plan.operation == DELEGATE_CALL:
        calls, multisend_failures = _multisend_failures(plan, transaction)
        failures += multisend_failures
    else:
        failures += _empty_transaction_failures(transaction)
    return VerificationReport(
        plan_hash=plan.plan_hash,
        safe_tx_hash=safe_tx_hash,
        calls=calls,
        failures=tuple(failures),
    )


def _identity_failures(plan: PayoutPlan, transaction: SafeTransaction) -> list[str]:
    failures = []
    if transaction.chain_id != plan.chain_id:
        failures.append(
            f"chain id: transaction is for chain {transaction.chain_id}, "
            f"plan expects {plan.chain_id}"
        )
    if transaction.safe != plan.safe:
        failures.append(
            f"Safe: transaction belongs to {transaction.safe}, plan expects {plan.safe}"
        )
    if transaction.nonce != plan.nonce:
        failures.append(
            f"nonce: transaction has nonce {transaction.nonce}, "
            f"plan expects {plan.nonce}"
        )
    if transaction.to != plan.to:
        failures.append(
            f"target: transaction calls {transaction.to}, plan expects {plan.to}"
        )
    if transaction.operation != plan.operation:
        failures.append(
            f"operation: transaction uses {_OPERATION_NAMES[transaction.operation]}, "
            f"plan expects {_OPERATION_NAMES[plan.operation]}"
        )
    return failures


def _execution_parameter_failures(transaction: SafeTransaction) -> list[str]:
    failures = []
    if transaction.value != 0:
        failures.append(f"value: transaction sends {transaction.value} wei, expected 0")
    for name, amount in (
        ("safeTxGas", transaction.safe_tx_gas),
        ("baseGas", transaction.base_gas),
        ("gasPrice", transaction.gas_price),
    ):
        if amount != 0:
            failures.append(f"gas refund: {name} is {amount}, expected 0")
    for name, address in (
        ("gasToken", transaction.gas_token),
        ("refundReceiver", transaction.refund_receiver),
    ):
        if address != ZERO_ADDRESS:
            failures.append(f"gas refund: {name} is {address}, expected {ZERO_ADDRESS}")
    return failures


def _multisend_failures(
    plan: PayoutPlan, transaction: SafeTransaction
) -> tuple[tuple[PayoutCall, ...], list[str]]:
    failures = [
        f"target: {target} is not an approved MultiSendCallOnly contract"
        for target in dict.fromkeys((plan.to, transaction.to))
        if target not in APPROVED_MULTISEND_CONTRACTS
    ]
    try:
        calls = decode_payout_calls(transaction.data)
    except CalldataError as err:
        return (), failures + [f"calldata: {err}"]
    failures += _ordering_failures(calls)
    failures += _multiset_failures(plan.calls, calls)
    return tuple(calls), failures


def _empty_transaction_failures(transaction: SafeTransaction) -> list[str]:
    failures = []
    if transaction.to != transaction.safe:
        failures.append(
            f"empty transaction: calls {transaction.to}, expected the Safe itself"
        )
    if transaction.data:
        failures.append(
            f"empty transaction: has {len(transaction.data)} bytes of calldata, "
            "expected none"
        )
    return failures


def _ordering_failures(calls: Sequence[PayoutCall]) -> list[str]:
    positions = [
        index
        for index, call in enumerate(calls)
        if isinstance(call, WrappedNativeWithdrawal)
    ]
    if len(positions) > 1:
        return [
            f"ordering: wrapped native withdrawals at positions {positions}, "
            "at most one is allowed"
        ]
    if positions and positions[0] != 0:
        return [
            f"ordering: wrapped native withdrawal at position {positions[0]}, "
            "it must be the first call"
        ]
    return []


def _multiset_failures(
    expected: Sequence[PayoutCall], actual: Sequence[PayoutCall]
) -> list[str]:
    planned = Counter(expected)
    found = Counter(actual)
    failures = [
        f"missing: {call} (plan expects {count}, transaction has {found[call]})"
        for call, count in planned.items()
        if found[call] < count
    ]
    failures += [
        f"unexpected: {call} (transaction has {count}, plan expects {planned[call]})"
        for call, count in found.items()
        if planned[call] < count
    ]
    return failures


def _totals(calls: Sequence[PayoutCall]) -> list[str]:
    totals: dict[str, tuple[int, int]] = {}
    for call in calls:
        if isinstance(call, NativeTransfer):
            key = "native transfers (wei)"
        elif isinstance(call, Erc20Transfer):
            key = f"ERC-20 transfers of {call.token} (atoms)"
        else:
            key = f"withdrawals from {call.token} (wei)"
        count, amount = totals.get(key, (0, 0))
        totals[key] = (count + 1, amount + call.amount)
    return [
        f"{key}: {count} calls, total {amount}"
        for key, (count, amount) in totals.items()
    ]
