"""Payout plans: the atom-exact intent a Safe transaction is verified against.

A payout plan describes exactly one Safe transaction the payout script
intends to propose. Schema version 1 is a JSON object with exactly these
members:

    {
      "schemaVersion": 1,
      "runId": "2026-06-16-arbitrum-1",
      "network": "arbitrum",
      "accountingPeriod": "2026-06-16-to-2026-06-23",
      "generatorCommit": "<40 lowercase hex digits>",
      "configHash": "0x<64 lowercase hex digits>",
      "chainId": 42161,
      "safe": "0x66331f0b9cb30d38779c786Bda5a3d57d12fbA50",
      "nonce": 213,
      "to": "0x40A2aCCbd92BCA938b02010E17A5b8929b49130D",
      "operation": 1,
      "calls": [
        {"callType": "wrappedNativeWithdrawal", "token": "0x...",
         "amountAtoms": "6435645361627000999"},
        {"callType": "nativeTransfer", "recipient": "0x...",
         "amountAtoms": "68168977168730428"},
        {"callType": "erc20Transfer", "token": "0x...", "recipient": "0x...",
         "amountAtoms": "5000"}
      ],
      "planHash": "0x<64 lowercase hex digits>"
    }

- ``network`` is the ``src.config.Network`` value of the accounting run and
  ``accountingPeriod`` is ``str(AccountingPeriod)``. ``chainId`` is the chain
  the transaction executes on: COW rewards for every network are paid on
  mainnet.
- ``operation`` 1 (DELEGATECALL) is a MultiSend with at least one call;
  operation 0 (CALL) is the empty nonce-reservation transaction, which has
  ``to`` equal to ``safe`` and no calls.
- Amounts are ``amountAtoms`` strings of ASCII decimal digits without leading
  zeros, greater than zero and below 2**256. No member of the document may be
  a floating-point number, NaN or infinity, and objects may not repeat keys.
- At most one ``wrappedNativeWithdrawal`` is allowed.
- ``planHash`` is ``"0x" + sha256(canonical)``, where ``canonical`` is the
  document without ``planHash`` serialised with sorted keys, no whitespace and
  ASCII escapes (``json.dumps(..., sort_keys=True, separators=(",", ":"))``).

Anything else is rejected with ``PayoutPlanError``.
"""

from __future__ import annotations

import hashlib
import json
import re
from collections.abc import Mapping
from dataclasses import dataclass
from datetime import datetime
from pathlib import Path
from typing import Any, NoReturn

from eth_typing.evm import ChecksumAddress

from src.verification.calldata import (
    CALL,
    DELEGATE_CALL,
    Erc20Transfer,
    NativeTransfer,
    PayoutCall,
    WrappedNativeWithdrawal,
    parse_address,
    parse_uint,
)

SCHEMA_VERSION = 1

NATIVE_TRANSFER = "nativeTransfer"
ERC20_TRANSFER = "erc20Transfer"
WRAPPED_NATIVE_WITHDRAWAL = "wrappedNativeWithdrawal"

_PLAN_FIELDS = frozenset(
    {
        "schemaVersion",
        "runId",
        "network",
        "accountingPeriod",
        "generatorCommit",
        "configHash",
        "chainId",
        "safe",
        "nonce",
        "to",
        "operation",
        "calls",
        "planHash",
    }
)
_CALL_FIELDS = {
    NATIVE_TRANSFER: frozenset({"callType", "recipient", "amountAtoms"}),
    ERC20_TRANSFER: frozenset({"callType", "token", "recipient", "amountAtoms"}),
    WRAPPED_NATIVE_WITHDRAWAL: frozenset({"callType", "token", "amountAtoms"}),
}
_RUN_ID = re.compile(r"[A-Za-z0-9][A-Za-z0-9._:-]{0,127}")
_NETWORK = re.compile(r"[a-z][a-z0-9_-]{0,63}")
_PERIOD = re.compile(r"([0-9]{4}-[0-9]{2}-[0-9]{2})-to-([0-9]{4}-[0-9]{2}-[0-9]{2})")
_COMMIT = re.compile(r"[0-9a-f]{40}")
_HASH = re.compile(r"0x[0-9a-f]{64}")


class PayoutPlanError(ValueError):
    """The payout plan does not conform to the schema."""


@dataclass(frozen=True)
class PayoutPlan:
    """A validated payout plan for one Safe transaction."""

    # pylint: disable=too-many-instance-attributes

    schema_version: int
    run_id: str
    network: str
    accounting_period: str
    generator_commit: str
    config_hash: str
    chain_id: int
    safe: ChecksumAddress
    nonce: int
    to: ChecksumAddress
    operation: int
    calls: tuple[PayoutCall, ...]
    plan_hash: str


def plan_hash(document: Mapping[str, Any]) -> str:
    """Hash of a plan document, ignoring its ``planHash`` member."""
    body = {key: value for key, value in document.items() if key != "planHash"}
    canonical = json.dumps(
        body, sort_keys=True, separators=(",", ":"), ensure_ascii=True, allow_nan=False
    )
    return "0x" + hashlib.sha256(canonical.encode("ascii")).hexdigest()


def load_payout_plan(path: str | Path) -> PayoutPlan:
    """Read and validate a payout plan file."""
    with open(path, encoding="utf-8") as file:
        return parse_payout_plan(file.read())


def parse_payout_plan(text: str) -> PayoutPlan:
    """Parse and validate a payout plan from JSON text."""
    try:
        document = json.loads(
            text,
            parse_float=_reject_float,
            parse_constant=_reject_constant,
            object_pairs_hook=_reject_duplicate_keys,
        )
    except PayoutPlanError:
        raise
    except ValueError as err:
        raise PayoutPlanError(f"not valid JSON: {err}") from err
    return payout_plan_from_document(document)


def payout_plan_from_document(document: object) -> PayoutPlan:
    """Validate an already parsed plan document.

    Every member is validated before ``planHash`` is compared, so a malformed
    member is reported as such rather than as a hash mismatch.
    """
    members = _exact_members(document, _PLAN_FIELDS, "plan")
    if _json_integer(members["schemaVersion"], "schemaVersion") != SCHEMA_VERSION:
        _fail(f"schemaVersion: unsupported version {members['schemaVersion']}")
    plan = PayoutPlan(
        schema_version=SCHEMA_VERSION,
        run_id=_text(members["runId"], "runId", _RUN_ID),
        network=_text(members["network"], "network", _NETWORK),
        accounting_period=_accounting_period(members["accountingPeriod"]),
        generator_commit=_text(members["generatorCommit"], "generatorCommit", _COMMIT),
        config_hash=_text(members["configHash"], "configHash", _HASH),
        chain_id=_json_integer(members["chainId"], "chainId"),
        safe=_address(members["safe"], "safe"),
        nonce=_json_integer(members["nonce"], "nonce"),
        to=_address(members["to"], "to"),
        operation=_json_integer(members["operation"], "operation"),
        calls=_calls(members["calls"]),
        plan_hash=_text(members["planHash"], "planHash", _HASH),
    )
    if plan.chain_id == 0:
        _fail("chainId: must be positive")
    if plan.operation not in (CALL, DELEGATE_CALL):
        _fail(f"operation: {plan.operation} is neither 0 (CALL) nor 1 (DELEGATECALL)")
    if plan.operation == DELEGATE_CALL and not plan.calls:
        _fail("calls: a MultiSend transaction needs at least one call")
    if plan.operation == CALL and (plan.calls or plan.to != plan.safe):
        _fail("calls: an operation 0 transaction must be empty and call the Safe")
    withdrawals = sum(isinstance(call, WrappedNativeWithdrawal) for call in plan.calls)
    if withdrawals > 1:
        _fail(f"calls: {withdrawals} wrapped native withdrawals, at most one allowed")
    computed = plan_hash(members)
    if plan.plan_hash != computed:
        _fail(f"planHash: declared {plan.plan_hash}, but the plan hashes to {computed}")
    return plan


def _fail(message: str) -> NoReturn:
    raise PayoutPlanError(message)


def _reject_float(literal: str) -> NoReturn:
    _fail(f"floating-point number {literal} is not allowed")


def _reject_constant(literal: str) -> NoReturn:
    _fail(f"{literal} is not allowed")


def _reject_duplicate_keys(pairs: list[tuple[str, Any]]) -> dict[str, Any]:
    result: dict[str, Any] = {}
    for key, value in pairs:
        if key in result:
            _fail(f"duplicate key {key!r}")
        result[key] = value
    return result


def _exact_members(
    value: object, expected: frozenset[str], what: str
) -> dict[str, Any]:
    if not isinstance(value, dict):
        _fail(f"{what}: expected a JSON object")
    missing = sorted(expected - value.keys())
    unknown = sorted(value.keys() - expected)
    if missing:
        _fail(f"{what}: missing {', '.join(missing)}")
    if unknown:
        _fail(f"{what}: unknown {', '.join(unknown)}")
    return value


def _json_integer(value: object, what: str) -> int:
    if not isinstance(value, int) or isinstance(value, bool):
        _fail(f"{what}: expected a JSON integer, got {value!r}")
    try:
        return parse_uint(value, what)
    except ValueError as err:
        raise PayoutPlanError(str(err)) from err


def _amount(value: object, what: str) -> int:
    if not isinstance(value, str):
        _fail(f"{what}: expected a decimal string, got {value!r}")
    try:
        amount = parse_uint(value, what)
    except ValueError as err:
        raise PayoutPlanError(str(err)) from err
    if amount == 0:
        _fail(f"{what}: must be greater than zero")
    return amount


def _address(value: object, what: str) -> ChecksumAddress:
    try:
        return parse_address(value, what)
    except ValueError as err:
        raise PayoutPlanError(str(err)) from err


def _text(value: object, what: str, pattern: re.Pattern[str]) -> str:
    if not isinstance(value, str) or not pattern.fullmatch(value):
        _fail(f"{what}: {value!r} does not match {pattern.pattern}")
    return value


def _accounting_period(value: object) -> str:
    match = _PERIOD.fullmatch(value) if isinstance(value, str) else None
    if match is None:
        _fail(f"accountingPeriod: {value!r} is not START-to-END")
    try:
        start, end = (datetime.strptime(date, "%Y-%m-%d") for date in match.groups())
    except ValueError as err:
        raise PayoutPlanError(f"accountingPeriod: {err}") from err
    if start >= end:
        _fail(f"accountingPeriod: {value!r} does not end after it starts")
    return match.group(0)


def _calls(value: object) -> tuple[PayoutCall, ...]:
    if not isinstance(value, list):
        _fail("calls: expected a JSON array")
    return tuple(_call(item, f"calls[{index}]") for index, item in enumerate(value))


def _call(item: object, what: str) -> PayoutCall:
    call_type = item.get("callType") if isinstance(item, dict) else None
    if not isinstance(call_type, str) or call_type not in _CALL_FIELDS:
        _fail(f"{what}: unknown callType {call_type!r}")
    call = _exact_members(item, _CALL_FIELDS[call_type], what)
    amount = _amount(call["amountAtoms"], f"{what}.amountAtoms")
    if call_type == NATIVE_TRANSFER:
        return NativeTransfer(
            recipient=_address(call["recipient"], f"{what}.recipient"), amount=amount
        )
    if call_type == ERC20_TRANSFER:
        return Erc20Transfer(
            token=_address(call["token"], f"{what}.token"),
            recipient=_address(call["recipient"], f"{what}.recipient"),
            amount=amount,
        )
    return WrappedNativeWithdrawal(
        token=_address(call["token"], f"{what}.token"), amount=amount
    )
