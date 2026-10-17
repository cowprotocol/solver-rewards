"""Same-run attestation on CoW's real payout code.

CoW's unmodified ``auto_propose`` proposes the transactions of one mocked
Arbitrum accounting run (``scenarios``) offline (``proposal_capture``). The
plans are built with ``expected_calls`` and ``plan_builder`` from the same
run's payout intent: its ``Transfer`` objects, the native balance its node
serves and the nonces of the oracle in ``scenarios``. They are never built
from a captured transaction.

1. The honest COW, empty and native transactions pass.
2. A changed transaction fails, naming the change.
3. A plan from another run fails with exactly the differences.
4. Buggy construction code builds a wrong transaction from the same intent,
   the plan stays the same, and verification fails.
5. The overdrafts transaction is captured and refused.
6. The run reads the chain, posts and waits exactly as expected.
"""

from __future__ import annotations

import unittest
from collections.abc import Callable
from dataclasses import dataclass, replace
from typing import Any
from unittest.mock import patch

from dune_client.types import Address
from eth_typing.evm import ChecksumAddress
from eth_utils.address import to_checksum_address
from safe_eth.eth.ethereum_client import EthereumClient
from safe_eth.safe.multi_send import MultiSend, MultiSendOperation, MultiSendTx

from src.fetch import transfer_file
from src.models.transfer import Transfer
from src.multisend import prepend_unwrap_if_necessary
from src.verification.calldata import (
    Erc20Transfer,
    NativeTransfer,
    PayoutCall,
    WrappedNativeWithdrawal,
)
from src.verification.expected_calls import cow_multisend_calls, native_multisend_calls
from src.verification.plan_builder import (
    BuiltPlan,
    empty_transaction_plan,
    multisend_plan,
)
from src.verification.strict_verifier import VerificationReport, verify_safe_transaction
from tests.unit.safe_transaction_fixtures import producer_encoding
from tests.unit.same_run.fake_node import RpcRequest
from tests.unit.same_run.proposal_capture import (
    ProposalRun,
    ProposedTransaction,
    propose,
)
from tests.unit.same_run.scenarios import (
    ARBITRUM_CHAIN_ID,
    ARBITRUM_SAFE,
    COW_TOKEN,
    MAINNET_CHAIN_ID,
    MAINNET_SAFE,
    MULTISEND_CALL_ONLY_V150,
    SLACK_CHANNEL,
    SOLVER_B,
    SOLVER_C,
    SOLVER_D,
    WRAPPED_NATIVE_TOKEN,
    ExpectedNonces,
    PayoutScenario,
    arbitrum_run,
)

# The transactions of a run, in posting order.
COW, EMPTY, NATIVE, OVERDRAFTS = range(4)

# The native transfers pay 1679012223467901222 wei; the Safe holds
# 456789012345678901 wei.
HONEST_UNWRAP = 1_222_223_211_122_222_321

ATTACKER = to_checksum_address("0x" + "ba5e" * 10)
WRONG_RECIPIENT = to_checksum_address("0x" + "0e" * 20)

ETH_SERVICE = "https://api.safe.global/tx-service/eth"
ARB1_SERVICE = "https://api.safe.global/tx-service/arb1"

# Calldata of the contract reads: VERSION(), nonce() and
# balanceOf(ARBITRUM_SAFE).
VERSION_CALL = "0xffa1ad74"
NONCE_CALL = "0xaffed0e0"
BALANCE_OF_ARBITRUM_SAFE = (
    "0x70a08231" + "0" * 24 + "66331f0b9cb30d38779c786bda5a3d57d12fba50"
)


@dataclass(frozen=True)
class RunPlans:
    """The plans of a run's COW, empty and native transactions."""

    cow: BuiltPlan
    empty: BuiltPlan
    native: BuiltPlan


def native_calls(scenario: PayoutScenario) -> tuple[PayoutCall, ...]:
    """The calls of the run's native transaction, from its native list."""
    return native_multisend_calls(
        scenario.transfers_native,
        native_balance=scenario.native_balance,
        wrapped_native_token=WRAPPED_NATIVE_TOKEN,
    )


def plans_for(scenario: PayoutScenario) -> RunPlans:
    """The plans of a run, from its payout intent and the oracle's nonces."""
    nonces = scenario.expected_nonces()
    return RunPlans(
        cow=multisend_plan(
            chain_id=MAINNET_CHAIN_ID,
            safe=MAINNET_SAFE,
            nonce=nonces.cow,
            calls=cow_multisend_calls(scenario.transfers_cow),
            provenance=scenario.provenance,
        ),
        empty=empty_transaction_plan(
            chain_id=ARBITRUM_CHAIN_ID,
            safe=ARBITRUM_SAFE,
            nonce=nonces.empty,
            provenance=scenario.provenance,
        ),
        native=multisend_plan(
            chain_id=ARBITRUM_CHAIN_ID,
            safe=ARBITRUM_SAFE,
            nonce=nonces.native,
            calls=native_calls(scenario),
            provenance=scenario.provenance,
        ),
    )


def verify(plan: BuiltPlan, proposal: ProposedTransaction) -> VerificationReport:
    """Verify a proposal, given the safeTxHash reported for it."""
    return verify_safe_transaction(
        plan.plan, proposal.transaction, reported_safe_tx_hash=proposal.safe_tx_hash
    )


def changed(
    proposal: ProposedTransaction,
    edit: Callable[[list[MultiSendTx]], list[MultiSendTx]],
) -> ProposedTransaction:
    """The proposal with its MultiSend rebuilt from edited inner calls, and
    the safeTxHash the Transaction Service would then report for it."""
    calls = MultiSend.from_transaction_data(proposal.transaction.data)
    transaction = replace(proposal.transaction, data=producer_encoding(edit(calls)))
    return replace(
        proposal, transaction=transaction, safe_tx_hash=transaction.safe_tx_hash()
    )


def one_atom_more(call: MultiSendTx) -> MultiSendTx:
    """The same ERC-20 transfer, of one atom more."""
    data = bytes(call.data)
    amount = int.from_bytes(data[-32:], "big") + 1
    return MultiSendTx(
        call.operation, call.to, call.value, data[:-32] + amount.to_bytes(32, "big")
    )


def withdrawal(amount: int) -> WrappedNativeWithdrawal:
    """A withdrawal of ``amount`` wei from the wrapped native token."""
    return WrappedNativeWithdrawal(WRAPPED_NATIVE_TOKEN, amount)


def missing(call: PayoutCall) -> str:
    """The failure for a planned call the transaction does not make."""
    return f"missing: {call} (plan expects 1, transaction has 0)"


def unexpected(call: PayoutCall) -> str:
    """The failure for a call the transaction makes and the plan does not list."""
    return f"unexpected: {call} (transaction has 1, plan expects 0)"


def client_reads() -> tuple[RpcRequest, ...]:
    """EthereumClient's constructor reads the chain id; web3 reads it once
    more before it caches it."""
    return (RpcRequest("eth_chainId", []), RpcRequest("eth_chainId", []))


def call_read(to: str, data: str) -> RpcRequest:
    """An ``eth_call`` at the latest block."""
    return RpcRequest("eth_call", [{"to": to, "data": data}, "latest"])


def safe_reads(safe: str) -> tuple[RpcRequest, ...]:
    """``Safe(...)`` reads ``VERSION()``, ``retrieve_nonce()`` reads ``nonce()``."""
    return (call_read(safe, VERSION_CALL), call_read(safe, NONCE_CALL))


def multisend_reads(safe: str) -> tuple[RpcRequest, ...]:
    """MultiSend finds a deployed MultiSendCallOnly, then the Safe is read."""
    get_code = RpcRequest("eth_getCode", [MULTISEND_CALL_ONLY_V150, "latest"])
    return (get_code, *safe_reads(safe))


def balance_reads() -> tuple[RpcRequest, ...]:
    """``prepend_unwrap_if_necessary`` reads the Safe's native balance and,
    as it is short, its wrapped native token balance."""
    return (
        RpcRequest("eth_getBalance", [ARBITRUM_SAFE, "latest"]),
        call_read(WRAPPED_NATIVE_TOKEN, BALANCE_OF_ARBITRUM_SAFE),
    )


class SameRunTestCase(unittest.TestCase):
    """The honest run, its plans, and the checks of a failing verification."""

    honest: ProposalRun
    plans: RunPlans

    @classmethod
    def setUpClass(cls) -> None:
        cls.honest = propose(arbitrum_run())
        cls.plans = plans_for(arbitrum_run())

    def assert_fails(
        self, report: VerificationReport, failures: tuple[str, ...]
    ) -> None:
        """The report fails with exactly ``failures``, in this order."""
        self.assertEqual(report.failures, failures)
        self.assertFalse(report.passed)


class TestHonestRun(SameRunTestCase):
    """Case 1: the honest transactions pass."""

    def test_transactions_are_proposed_at_the_oracle_nonces(self) -> None:
        """Four transactions, in posting order, at the oracle's nonces."""
        nonces = arbitrum_run().expected_nonces()
        self.assertEqual(
            nonces, ExpectedNonces(cow=1462, empty=260, native=261, overdrafts=262)
        )
        self.assertEqual(
            [
                (proposal.transaction.chain_id, proposal.transaction.safe)
                for proposal in self.honest.proposals
            ],
            [(MAINNET_CHAIN_ID, MAINNET_SAFE)]
            + [(ARBITRUM_CHAIN_ID, ARBITRUM_SAFE)] * 3,
        )
        self.assertEqual(
            [proposal.transaction.nonce for proposal in self.honest.proposals],
            [nonces.cow, nonces.empty, nonces.native, nonces.overdrafts],
        )

    def test_cow_transaction_passes(self) -> None:
        """The COW transaction pays exactly the COW transfers."""
        self.assert_passes(self.plans.cow, self.honest.proposals[COW])

    def test_empty_transaction_passes(self) -> None:
        """The empty transaction reserves the oracle's nonce."""
        self.assert_passes(self.plans.empty, self.honest.proposals[EMPTY])

    def test_native_transaction_passes(self) -> None:
        """The native transaction unwraps first, then pays the native list."""
        self.assert_passes(self.plans.native, self.honest.proposals[NATIVE])
        self.assertEqual(self.plans.native.plan.calls[0], withdrawal(HONEST_UNWRAP))

    def assert_passes(self, plan: BuiltPlan, proposal: ProposedTransaction) -> None:
        """The proposal passes, its recomputed safeTxHash is safe-eth-py's,
        and it makes exactly the planned calls, in the planned order."""
        report = verify(plan, proposal)
        self.assertEqual(report.failures, ())
        self.assertTrue(report.passed)
        self.assertEqual(report.safe_tx_hash, proposal.safe_tx_hash)
        self.assertEqual(report.calls, plan.plan.calls)


class TestChangedTransaction(SameRunTestCase):
    """Case 2: a changed transaction fails, naming the change."""

    def test_one_atom_more(self) -> None:
        """One atom more for SOLVER_B in the COW transaction."""
        proposal = changed(
            self.honest.proposals[COW],
            lambda calls: [calls[0], one_atom_more(calls[1]), *calls[2:]],
        )
        self.assert_fails(
            verify(self.plans.cow, proposal),
            (
                missing(Erc20Transfer(COW_TOKEN, SOLVER_B, 98_765_432_109_876_543_210)),
                unexpected(
                    Erc20Transfer(COW_TOKEN, SOLVER_B, 98_765_432_109_876_543_211)
                ),
            ),
        )

    def test_extra_call(self) -> None:
        """An extra native transfer at the end of the native transaction."""
        extra = MultiSendTx(MultiSendOperation.CALL, ATTACKER, 10**18, b"")
        proposal = changed(self.honest.proposals[NATIVE], lambda calls: [*calls, extra])
        self.assert_fails(
            verify(self.plans.native, proposal),
            (unexpected(NativeTransfer(ATTACKER, 10**18)),),
        )


class TestPlanFromAnotherRun(SameRunTestCase):
    """Case 3: the plan of another run of the period accepts that run's own
    native transaction and rejects this run's, with exactly the differences."""

    def test_other_native_balance(self) -> None:
        """The other run read 10**17 wei more native balance, so it unwraps
        that much less."""
        other = arbitrum_run().with_native_balance(556_789_012_345_678_901)
        self.assert_fails(
            self.verify_other_plan(other),
            (
                missing(withdrawal(1_122_223_211_122_222_321)),
                unexpected(withdrawal(HONEST_UNWRAP)),
            ),
        )

    def test_dropped_transfer(self) -> None:
        """The other run did not pay SOLVER_D's native transfer, so it also
        unwraps that much less."""
        other = arbitrum_run().without_native_transfer(2)
        self.assert_fails(
            self.verify_other_plan(other),
            (
                missing(withdrawal(1_123_457_779_012_345_778)),
                unexpected(withdrawal(HONEST_UNWRAP)),
                unexpected(NativeTransfer(SOLVER_D, 98_765_432_109_876_543)),
            ),
        )

    def verify_other_plan(self, other: PayoutScenario) -> VerificationReport:
        """Verify this run's native transaction against the other run's plan,
        once that plan has passed the other run's own native transaction."""
        plan = plans_for(other).native
        self.assertTrue(verify(plan, propose(other).proposals[NATIVE]).passed)
        return verify(plan, self.honest.proposals[NATIVE])


class TestConstructionBug(SameRunTestCase):
    """Case 4: buggy construction code builds a wrong native transaction from
    the run's intent. The plan, built from the same intent, does not change."""

    def test_swapped_recipient(self) -> None:
        """``Transfer.as_multisend_tx`` pays SOLVER_C's native transfer to
        another address."""
        scenario = arbitrum_run()
        victim = scenario.transfers_native[1]
        as_multisend_tx = Transfer.as_multisend_tx

        def swapped(transfer: Transfer) -> MultiSendTx:
            if transfer is victim:
                transfer = Transfer(
                    transfer.token, Address(WRONG_RECIPIENT), transfer.amount_wei
                )
            return as_multisend_tx(transfer)

        with patch.object(Transfer, "as_multisend_tx", swapped):
            buggy = self.run_with_bug(scenario)
        self.assert_fails(
            verify(self.plans.native, buggy.proposals[NATIVE]),
            (
                missing(NativeTransfer(SOLVER_C, 345_678_901_234_567_890)),
                unexpected(NativeTransfer(WRONG_RECIPIENT, 345_678_901_234_567_890)),
            ),
        )

    def test_unwrap_appended(self) -> None:
        """``prepend_unwrap_if_necessary`` appends the unwrap instead of
        prepending it. Only the order of the calls changes."""

        def unwrap_appended(
            client: EthereumClient,
            safe_address: ChecksumAddress,
            *,
            transactions: list[MultiSendTx],
            **kwargs: Any,
        ) -> list[MultiSendTx]:
            count = len(transactions)
            result = prepend_unwrap_if_necessary(
                client, safe_address, transactions=transactions, **kwargs
            )
            if len(result) > count:
                result.append(result.pop(0))
            return result

        with patch.object(
            transfer_file, "prepend_unwrap_if_necessary", unwrap_appended
        ):
            buggy = self.run_with_bug(arbitrum_run())
        self.assert_fails(
            verify(self.plans.native, buggy.proposals[NATIVE]),
            (
                "ordering: wrapped native withdrawal at position 6, "
                "it must be the first call",
            ),
        )

    def run_with_bug(self, scenario: PayoutScenario) -> ProposalRun:
        """Propose ``scenario`` with the bug in place. The plans built from it
        meanwhile equal the honest ones, and only the native transaction differs
        from the honest run's."""
        buggy = propose(scenario)
        self.assertEqual(plans_for(scenario), self.plans)
        for index, (honest, wrong) in enumerate(
            zip(self.honest.proposals, buggy.proposals, strict=True)
        ):
            if index == NATIVE:
                self.assertNotEqual(honest, wrong)
            else:
                self.assertEqual(honest, wrong)
        return buggy


class TestOverdrafts(SameRunTestCase):
    """Case 5: the overdrafts transaction is captured and refused."""

    def test_overdrafts_transaction_is_refused(self) -> None:
        """No plan can describe an overdraft. Against a payout plan for its
        Safe and nonce, the only failure is the decoder refusing addOverdraft:
        chain, Safe, nonce, target, operation and safeTxHash all match."""
        scenario = arbitrum_run()
        proposal = self.honest.proposals[OVERDRAFTS]
        plan = multisend_plan(
            chain_id=ARBITRUM_CHAIN_ID,
            safe=ARBITRUM_SAFE,
            nonce=scenario.expected_nonces().overdrafts,
            calls=native_calls(scenario),
            provenance=scenario.provenance,
        )
        report = verify(plan, proposal)
        self.assert_fails(
            report,
            (
                "calldata: inner transaction 0: unsupported function selector "
                "0xeb8e571d (addOverdraft(address,uint256)), this transaction type "
                "is not verified",
            ),
        )
        self.assertEqual(report.safe_tx_hash, proposal.safe_tx_hash)


class TestRunEdges(SameRunTestCase):
    """Case 6: the run reads the chain, posts and waits exactly as expected."""

    def test_mainnet_reads(self) -> None:
        """Mainnet: the chain id, then the reads for the COW transaction."""
        self.assertEqual(
            self.honest.mainnet_requests,
            (*client_reads(), *multisend_reads(MAINNET_SAFE)),
        )

    def test_arbitrum_reads(self) -> None:
        """Arbitrum: the chain id, the balances for the unwrap, then the reads
        for the empty, native and overdrafts transactions."""
        self.assertEqual(
            self.honest.arbitrum_requests,
            (
                *client_reads(),
                *balance_reads(),
                *safe_reads(ARBITRUM_SAFE),
                *multisend_reads(ARBITRUM_SAFE),
                *multisend_reads(ARBITRUM_SAFE),
            ),
        )

    def test_posts_pauses_and_slack(self) -> None:
        """Each transaction goes to its chain's Transaction Service and is
        followed by a 2 second pause; one Slack message goes to the run's
        channel, and the Slack client is not used directly."""
        self.assertEqual(
            [proposal.service_url for proposal in self.honest.proposals],
            [ETH_SERVICE, ARB1_SERVICE, ARB1_SERVICE, ARB1_SERVICE],
        )
        self.assertEqual(self.honest.sleeps, (2, 2, 2, 2))
        self.assertEqual(self.honest.slack_channels, (SLACK_CHANNEL,))
        self.assertEqual(self.honest.slack_client_calls, 0)


if __name__ == "__main__":
    unittest.main()
