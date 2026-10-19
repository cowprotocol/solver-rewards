"""Mocked payout inputs of one Arbitrum accounting run.

``arbitrum_run`` returns what ``main()`` in ``src/fetch/transfer_file.py``
hands to ``auto_propose`` for one accounting period on Arbitrum One, and what
the two chains report while the transactions are built:

- COW rewards, paid from the mainnet Safe;
- native token transfers to solvers, followed by the wrapped native token
  transfers ``construct_payouts`` adds: the net protocol fee and the partner
  fee tax to the protocol fee Safe, and the fee of the partner paid in the
  wrapped native token;
- one overdraft;
- an Arbitrum Safe holding less native token than the native transfers pay,
  so that ``prepend_unwrap_if_necessary`` prepends an unwrap;
- the nonces and the version of both Safes.

Every ``Token`` has explicit decimals: ``Token(address)`` asks a node for
them. Solver addresses and the signing key are synthetic.
"""

from __future__ import annotations

from dataclasses import dataclass, replace
from typing import Any

from dune_client.types import Address
from eth_utils.address import to_checksum_address
from eth_utils.crypto import keccak

from src.config import Network
from src.models.accounting_period import AccountingPeriod
from src.models.overdraft import Overdraft
from src.models.token import Token
from src.models.transfer import Transfer
from src.verification.plan_builder import PlanProvenance
from tests.unit.same_run.fake_node import ChainState, SafeState

MAINNET_CHAIN_ID = 1
ARBITRUM_CHAIN_ID = 42161

# The payout Safes of both networks.
MAINNET_SAFE = to_checksum_address("0xA03be496e67Ec29bC62F01a428683D7F9c204930")
ARBITRUM_SAFE = to_checksum_address("0x66331f0b9cb30d38779c786Bda5a3d57d12fbA50")
SAFE_VERSION = "1.3.0"

COW_TOKEN = to_checksum_address("0xDEf1CA1fb7FBcDC777520aa7f396b4E015F497aB")
# Arbitrum's wrapped native token, as src/config.py configures it.
WRAPPED_NATIVE_TOKEN = to_checksum_address("0x82aF49447D8a07e3bd95BD0d56f35241523fBab1")
PROTOCOL_FEE_SAFE = to_checksum_address("0x22af3D38E50ddedeb7C47f36faB321eC3Bb72A76")
# The partner whose fee src/config.py pays in the wrapped native token.
WRAPPED_NATIVE_PARTNER = to_checksum_address(
    "0x0A61B9F341a3ec8a8112D7dD6FBBC62B7FDF437e"
)
# safe-eth-py's MultiSend looks for a deployed MultiSendCallOnly, v1.5.0
# first, and finds it on both chains. The payout script targets v1.3.0.
MULTISEND_CALL_ONLY_V150 = to_checksum_address(
    "0xA83c336B20401Af773B6219BA5027174338D1836"
)
# MultiSend only checks that code is present, not what it is.
DEPLOYED_CODE = bytes.fromhex("fe")

SOLVER_A = to_checksum_address("0x" + "a1" * 20)
SOLVER_B = to_checksum_address("0x" + "b2" * 20)
SOLVER_C = to_checksum_address("0x" + "c3" * 20)
SOLVER_D = to_checksum_address("0x" + "d4" * 20)

# .invalid is reserved for names that are sure to be invalid (RFC 2606).
MAINNET_NODE_URL = "http://mainnet.node.invalid/"
ARBITRUM_NODE_URL = "http://arbitrum.node.invalid/"
SLACK_CHANNEL = "#same-run-test"

# Test-only signing key, derived from a public phrase. It signs nothing but
# the proposals these tests capture and must never hold funds.
TEST_ONLY_SIGNING_KEY = (
    "0x"
    + keccak(
        text="solver-rewards same-run attestation tests: test-only signing key"
    ).hex()
)

# The nonce_modifier of an Arbitrum run: the index of ARBITRUM_ONE in
# reversed(list(Network)), see PaymentConfig.from_network in src/config.py.
ARBITRUM_NONCE_MODIFIER = 7

ACCOUNTING_PERIOD = AccountingPeriod("2026-10-06")


@dataclass(frozen=True)
class ExpectedNonces:
    """The nonce of each transaction ``auto_propose`` proposes in one run."""

    cow: int
    empty: int
    native: int
    overdrafts: int


def expected_nonces(
    *,
    mainnet_safe_nonce: int,
    native_safe_nonce: int,
    nonce_modifier: int,
    native_posted: bool,
) -> ExpectedNonces:
    """Test oracle for a run whose payout network is not mainnet.

    Mirrors ``auto_propose`` in ``src/fetch/transfer_file.py`` at upstream
    commit 13b3671. The COW transaction takes the mainnet Safe's nonce plus
    the network's ``nonce_modifier``. On the payout network, the empty
    transaction takes the Safe's nonce and the native transaction the next
    one. The overdrafts transaction takes the nonce after the native
    transaction's, or the native transaction's own nonce when no native
    transaction was posted.
    """
    return ExpectedNonces(
        cow=mainnet_safe_nonce + nonce_modifier,
        empty=native_safe_nonce,
        native=native_safe_nonce + 1,
        overdrafts=native_safe_nonce + (2 if native_posted else 1),
    )


@dataclass(frozen=True)
class PayoutScenario:
    """The inputs of one accounting run: the payout intent ``auto_propose``
    is given, what the chains report, and the run's provenance."""

    # pylint: disable=too-many-instance-attributes

    transfers_cow: tuple[Transfer, ...]
    transfers_native: tuple[Transfer, ...]
    overdrafts: tuple[Overdraft, ...]
    mainnet_safe_nonce: int
    native_safe_nonce: int
    native_balance: int
    wrapped_native_balance: int
    provenance: PlanProvenance

    def environment(self) -> dict[str, str]:
        """The run's environment variables, from which ``AccountingConfig``
        is built. ``NONCE_MODIFIER`` is unset: the network's modifier applies.
        """
        return {
            "NETWORK": Network.ARBITRUM_ONE.value,
            "PROPOSER_PK": TEST_ONLY_SIGNING_KEY,
            "PAYOUTS_SAFE_ADDRESS_MAINNET": MAINNET_SAFE,
            "PAYOUTS_SAFE_ADDRESS": ARBITRUM_SAFE,
            "NODE_URL_MAINNET": MAINNET_NODE_URL,
            "NODE_URL": ARBITRUM_NODE_URL,
            "SLACK_CHANNEL": SLACK_CHANNEL,
        }

    def mainnet_chain(self) -> ChainState:
        """Mainnet, where the COW transaction is proposed."""
        return ChainState(
            chain_id=MAINNET_CHAIN_ID,
            code={MULTISEND_CALL_ONLY_V150: DEPLOYED_CODE},
            safes={MAINNET_SAFE: SafeState(self.mainnet_safe_nonce, SAFE_VERSION)},
        )

    def arbitrum_chain(self) -> ChainState:
        """Arbitrum One, where the native, empty and overdrafts transactions
        are proposed."""
        return ChainState(
            chain_id=ARBITRUM_CHAIN_ID,
            balances={ARBITRUM_SAFE: self.native_balance},
            code={MULTISEND_CALL_ONLY_V150: DEPLOYED_CODE},
            safes={ARBITRUM_SAFE: SafeState(self.native_safe_nonce, SAFE_VERSION)},
            token_balances={
                (WRAPPED_NATIVE_TOKEN, ARBITRUM_SAFE): self.wrapped_native_balance
            },
        )

    def expected_nonces(self) -> ExpectedNonces:
        """The oracle's nonces for this run."""
        return expected_nonces(
            mainnet_safe_nonce=self.mainnet_safe_nonce,
            native_safe_nonce=self.native_safe_nonce,
            nonce_modifier=ARBITRUM_NONCE_MODIFIER,
            native_posted=bool(self.transfers_native),
        )

    def with_native_balance(self, native_balance: int) -> PayoutScenario:
        """Another run of the period, which read another native balance."""
        return self._rerun(native_balance=native_balance)

    def without_native_transfer(self, index: int) -> PayoutScenario:
        """Another run of the period, without one native list transfer."""
        transfers = self.transfers_native[:index] + self.transfers_native[index + 1 :]
        return self._rerun(transfers_native=transfers)

    def _rerun(self, **changes: Any) -> PayoutScenario:
        run_id = self.provenance.run_id + "-rerun"
        return replace(
            self, provenance=replace(self.provenance, run_id=run_id), **changes
        )


def arbitrum_run() -> PayoutScenario:
    """The run. Each call builds new ``Transfer`` objects."""
    cow = Token(COW_TOKEN, 18)
    wrapped_native = Token(WRAPPED_NATIVE_TOKEN, 18)
    return PayoutScenario(
        transfers_cow=(
            Transfer(cow, Address(SOLVER_A), 412_345_678_901_234_567_890),
            Transfer(cow, Address(SOLVER_B), 98_765_432_109_876_543_210),
            Transfer(cow, Address(SOLVER_C), 7_000_000_000_000_000_001),
        ),
        transfers_native=(
            Transfer(None, Address(SOLVER_A), 1_234_567_890_123_456_789),
            Transfer(None, Address(SOLVER_C), 345_678_901_234_567_890),
            Transfer(None, Address(SOLVER_D), 98_765_432_109_876_543),
            # Net protocol fee, partner fee tax, then the partner's fee.
            Transfer(
                wrapped_native, Address(PROTOCOL_FEE_SAFE), 123_456_789_012_345_678
            ),
            Transfer(wrapped_native, Address(PROTOCOL_FEE_SAFE), 4_567_890_123_456_789),
            Transfer(
                wrapped_native, Address(WRAPPED_NATIVE_PARTNER), 23_456_789_012_345_678
            ),
        ),
        overdrafts=(
            Overdraft(
                ACCOUNTING_PERIOD, Address(SOLVER_B), "solver-b", 31_415_926_535_897_932
            ),
        ),
        # The run then proposes at the nonces the first Arbitrum payout run
        # after #642 used: 1462 on mainnet; 260, 261 and 262 on Arbitrum.
        mainnet_safe_nonce=1455,
        native_safe_nonce=260,
        # The native transfers pay 1679012223467901222 wei.
        native_balance=456_789_012_345_678_901,
        wrapped_native_balance=5 * 10**18,
        provenance=PlanProvenance(
            run_id="2026-10-06-arbitrum",
            network=Network.ARBITRUM_ONE.value,
            accounting_period=str(ACCOUNTING_PERIOD),
            # Provenance is supplied by the caller; these values only satisfy
            # the plan schema.
            generator_commit="0123456789abcdef" * 2 + "01234567",
            config_hash="0x" + "ab" * 32,
        ),
    )
