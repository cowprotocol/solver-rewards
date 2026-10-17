"""Canonical, hashed and validated payout plans for one Safe transaction.

A plan document in schema version 1 (see ``src.verification.payout_plan``) is
assembled from the identity of the Safe transaction, the provenance of the
payout run and the expected calls. Its ``planHash`` is computed with
``plan_hash`` and the document is validated by ``payout_plan_from_document``,
like every plan read from a file. Provenance is an input: the builder neither
computes nor checks it beyond the loader's rules.

- A MultiSend plan DELEGATECALLs ``MULTISEND_CALL_ONLY``, the contract
  ``post_multisend`` targets. It needs at least one call: ``post_multisend``
  proposes nothing for an empty list, and the loader rejects such a plan.
- An empty transaction plan CALLs the Safe itself and has no calls, like the
  transaction ``post_empty_transaction`` proposes.

Addresses are written as EIP-55 checksums whatever their input spelling, and
amounts as decimal strings, so the same plan always has the same document and
``planHash``. An invalid address raises ``ValueError``; anything else the
loader rejects raises its ``PayoutPlanError``.
"""

from __future__ import annotations

from collections.abc import Mapping, Sequence
from dataclasses import dataclass
from typing import Any

from eth_typing.evm import ChecksumAddress

from src.verification.calldata import (
    CALL,
    DELEGATE_CALL,
    Erc20Transfer,
    NativeTransfer,
    PayoutCall,
    parse_address,
)
from src.verification.payout_plan import (
    ERC20_TRANSFER,
    NATIVE_TRANSFER,
    SCHEMA_VERSION,
    WRAPPED_NATIVE_WITHDRAWAL,
    PayoutPlan,
    payout_plan_from_document,
    plan_hash,
)
from src.verification.strict_verifier import MULTISEND_CALL_ONLY


@dataclass(frozen=True)
class PlanProvenance:
    """The payout run a plan belongs to, and the code and configuration it used."""

    # pylint: disable=duplicate-code

    run_id: str
    network: str
    accounting_period: str
    generator_commit: str
    config_hash: str


@dataclass(frozen=True)
class BuiltPlan:
    """A schema version 1 plan document and the plan the loader validated it as."""

    document: Mapping[str, Any]
    plan: PayoutPlan


def multisend_plan(
    *,
    chain_id: int,
    safe: ChecksumAddress,
    nonce: int,
    calls: Sequence[PayoutCall],
    provenance: PlanProvenance,
) -> BuiltPlan:
    """The plan of the payout MultiSend transaction making ``calls``."""
    return _built_plan(
        provenance,
        {
            "chainId": chain_id,
            "safe": parse_address(safe, "safe"),
            "nonce": nonce,
            "to": MULTISEND_CALL_ONLY,
            "operation": DELEGATE_CALL,
            "calls": [
                _call_document(call, f"calls[{index}]")
                for index, call in enumerate(calls)
            ],
        },
    )


def empty_transaction_plan(
    *,
    chain_id: int,
    safe: ChecksumAddress,
    nonce: int,
    provenance: PlanProvenance,
) -> BuiltPlan:
    """The plan of the empty transaction that reserves ``nonce`` on ``safe``."""
    checksummed = parse_address(safe, "safe")
    return _built_plan(
        provenance,
        {
            "chainId": chain_id,
            "safe": checksummed,
            "nonce": nonce,
            "to": checksummed,
            "operation": CALL,
            "calls": [],
        },
    )


def _built_plan(
    provenance: PlanProvenance, transaction: Mapping[str, Any]
) -> BuiltPlan:
    document: dict[str, Any] = {
        "schemaVersion": SCHEMA_VERSION,
        "runId": provenance.run_id,
        "network": provenance.network,
        "accountingPeriod": provenance.accounting_period,
        "generatorCommit": provenance.generator_commit,
        "configHash": provenance.config_hash,
        **transaction,
    }
    document["planHash"] = plan_hash(document)
    return BuiltPlan(document=document, plan=payout_plan_from_document(document))


def _call_document(call: PayoutCall, what: str) -> dict[str, str]:
    if isinstance(call, NativeTransfer):
        return {
            "callType": NATIVE_TRANSFER,
            "recipient": parse_address(call.recipient, f"{what}.recipient"),
            "amountAtoms": str(call.amount),
        }
    if isinstance(call, Erc20Transfer):
        return {
            "callType": ERC20_TRANSFER,
            "token": parse_address(call.token, f"{what}.token"),
            "recipient": parse_address(call.recipient, f"{what}.recipient"),
            "amountAtoms": str(call.amount),
        }
    return {
        "callType": WRAPPED_NATIVE_WITHDRAWAL,
        "token": parse_address(call.token, f"{what}.token"),
        "amountAtoms": str(call.amount),
    }
