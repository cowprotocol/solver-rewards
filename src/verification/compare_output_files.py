#!/usr/bin/env python3
"""Verify that solver-rewards transfers match the rewards reported by Dune.

Solver-rewards / fee data can come from either:
  - Dune, fetched automatically via --start (accounting period start date); or
  - manually-downloaded CSVs (dune_csv, --fees-csv, --partner-fees-csv).

Safe transaction data can come from either:
  - pasted Safe multisend calldata (--cow-transfers-calldata(-file),
    --native-transfers-calldata(-file), --overdraft-calldata(-file)); or
  - manually-downloaded Safe transaction-export CSVs (--cow-safe-csv,
    --native-safe-csv); or
  - a single combined transfers CSV with columns token_type, token_address,
    receiver, amount (the `transfers_csv` positional argument).

    Usage:
        scripts/verify_payout.sh --start 2026-09-08 --network bnb

        python3 -m src.verification.compare_output_files --start 2026-09-08 \\
            --network bnb \\
            --cow-transfers-calldata-file cow.txt \\
            --native-transfers-calldata-file native.txt

        python3 -m src.verification.compare_output_files DUNE_CSV \\
            --cow-safe-csv MAINNET_SAFE.csv \\
            --native-safe-csv NETWORK_SAFE.csv \\
            --network arbitrum

Safe CSV columns (transaction export format):
    Nonce, Safe Address, From Address, To Address, Transaction Hash,
    Contract Address, Amount, Asset Type, Asset Symbol, ...

The Dune CSV must contain at minimum:
    name, solver_address, reward_target, quote_reward,
    native_token_transfer, cow_transfer, overdraft

Exit status is 0 if no errors were found (warnings are still reported), and 1
otherwise. A missing or unmatched transfer above the native/COW threshold is
an error; below it, a warning.
"""

# The whole verification flow - parsing, comparison, reporting, CLI - deliberately
# lives in this one module so it can be read top-to-bottom before signing a payout.
# pylint: disable=too-many-lines

from __future__ import annotations

import argparse
import csv
import os
import sys
from dataclasses import dataclass, field
from typing import Any, Callable, Optional, TypeVar

# COW is deployed at the same address on every supported network.
COW_TOKEN_ADDRESS = "0xdef1ca1fb7fbcdc777520aa7f396b4e015f497ab"

# Networks the rewards may be generated for (kept in sync with src.config.Network,
# duplicated here rather than imported so this script has no hard dependency on
# unrelated environment variables such as NODE_URL when only doing CSV comparison).
NETWORKS = (
    "mainnet",
    "gnosis",
    "arbitrum",
    "base",
    "avalanche",
    "polygon",
    "bnb",
    "linea",
    "plasma",
    "ink",
)

# Wrapped native token per network (kept in sync with
# src.config.PaymentConfig.wrapped_native_token_address, duplicated for the same reason as
# NETWORKS). The payout script sends the protocol fee, the partner fee tax and the fees of
# partners in ProtocolFeeConfig.partners_with_wrapped_native_transfers in this token, as
# ERC-20 transfers inside the native-transfer multisend.
WRAPPED_NATIVE_TOKEN_ADDRESSES = {
    "mainnet": "0xc02aaa39b223fe8d0a0e5c4f27ead9083c756cc2",
    "gnosis": "0xe91d153e0b41518a2ce8dd3d7944fa863463a97d",
    "arbitrum": "0x82af49447d8a07e3bd95bd0d56f35241523fbab1",
    "base": "0x4200000000000000000000000000000000000006",
    "avalanche": "0xb31f66aa3c1e785363f0875a1b74e27b85fd66c7",
    "polygon": "0x0d500b1d8e8ef31e21c99d1db9a6444d3adf1270",
    "bnb": "0xbb4cdb9cbd36b01bd1cbaebf2de08d9173bc095c",
    "linea": "0xe5d7c2a44ffddf6b295a15c148167daaaf5cf34f",
    "plasma": "0x6100e367285b01f48d07953803a2d8dca5d19873",
    "ink": "0x4200000000000000000000000000000000000006",
}

# The payout script drops transfers below these amounts instead of sending them (kept in
# sync with src.config.PaymentConfig.min_cow_transfer / min_native_token_transfer). An
# expected transfer below them that is missing is therefore skipped, not reported.
MIN_COW_TRANSFER = 1.0
MIN_NATIVE_TRANSFER = 10**6 / 10**18

# A missing or unmatched transfer above these amounts is an error; below, a warning.
DEFAULT_COW_THRESHOLD = 1.0
DEFAULT_NATIVE_THRESHOLD = 0.001
DEFAULT_TOLERANCE = (
    0.0001  # Max relative difference allowed between Dune and transfer amounts.
)


def parse_amount(value: object) -> float:
    """Parses a numeric field from either a CSV row (str) or a Dune API row (float/int).

    ``csv.DictReader`` always yields strings, but rows fetched directly from the Dune
    API come back with their native JSON types (numbers as float/int, not str).
    """
    if value is None or value == "":
        return 0.0
    if isinstance(value, str):
        value = value.strip()
        return float(value) if value else 0.0
    return float(value)  # type: ignore[arg-type]


@dataclass(frozen=True)
class DuneReward:
    """A single solver's reward data from the Dune export."""

    name: str
    solver_address: str
    reward_target: str
    quote_reward: float
    native_token_transfer: float
    cow_transfer: float
    overdraft: float = 0.0

    @property
    def solver_name(self) -> str:
        """The solver's name without its "prod-"/"barn-" environment prefix."""
        _, _, rest = self.name.partition("-")
        return rest or self.name

    @classmethod
    def from_csv_row(cls, row: dict) -> "DuneReward":
        """Parse a DuneReward from a CSV DictReader row (or an equivalent Dune API row).

        ``name``, ``reward_target``, and ``solver_address`` can come back null for a
        solver with nothing to pay out this period; that's harmless since every
        threshold check below is gated on a nonzero amount, so an empty value here
        never needs to be matched against a transfer.
        """
        return cls(
            name=row.get("name") or "",
            solver_address=(row.get("solver_address") or "").strip().lower(),
            reward_target=(row.get("reward_target") or "").strip().lower(),
            quote_reward=parse_amount(row.get("quote_reward")),
            native_token_transfer=parse_amount(row.get("native_token_transfer")),
            cow_transfer=parse_amount(row.get("cow_transfer")),
            overdraft=parse_amount(row.get("overdraft")),
        )


@dataclass(frozen=True)
class Transfer:
    """A single token transfer (ERC-20 or native)."""

    token_type: str
    token_address: str
    receiver: str
    amount: float

    @classmethod
    def from_csv_row(cls, row: dict) -> "Transfer":
        """Parse a Transfer from a CSV DictReader row."""
        return cls(
            token_type=row["token_type"].strip().lower(),
            token_address=row["token_address"].strip().lower(),
            receiver=row["receiver"].strip().lower(),
            amount=float(row["amount"]),
        )

    @property
    def is_wrapped_native(self) -> bool:
        """True for a native-value transfer made in the wrapped native token (e.g. WETH).

        Such transfers have token_type "native" and the wrapped token as token_address;
        plain native transfers have an empty token_address.
        """
        return self.token_type == "native" and bool(self.token_address)

    def __str__(self) -> str:
        if self.is_wrapped_native:
            return (
                f"wrapped native transfer of {self.amount} ({self.token_address}) "
                f"to {self.receiver}"
            )
        if self.token_type == "native":
            return f"native transfer of {self.amount} to {self.receiver}"
        return (
            f"erc20 transfer of {self.amount} ({self.token_address}) to {self.receiver}"
        )


def load_dune_rewards(path: str) -> list[DuneReward]:
    """Load and sort Dune rewards from a CSV file."""
    with open(path, newline="", encoding="utf-8") as f:
        rewards = [DuneReward.from_csv_row(row) for row in csv.DictReader(f)]
    # The rewards script processes solvers sorted by address.
    return sorted(rewards, key=lambda r: r.solver_address)


def load_transfers(path: str) -> list[Transfer]:
    """Load transfers from a combined transfers CSV."""
    with open(path, newline="", encoding="utf-8") as f:
        return [Transfer.from_csv_row(row) for row in csv.DictReader(f)]


_ZERO_ADDRESS = "0x" + "0" * 40


def load_safe_transfers(path: str, cow_token_address: str) -> list[Transfer]:
    """Load outgoing transfers from a Safe transaction-export CSV.

    Skips incoming rows (From Address != Safe Address) and WETH-unwrap burns
    (To Address == zero address).  ERC-20 rows are assigned cow_token_address
    as their token address (Safe exports do not include the token contract).
    """
    transfers: list[Transfer] = []
    with open(path, newline="", encoding="utf-8-sig") as f:
        for row in csv.DictReader(f):
            safe_addr = row.get("Safe Address", "").strip().lower()
            from_addr = row.get("From Address", "").strip().lower()
            to_addr = row.get("To Address", "").strip().lower()
            amount_str = row.get("Amount", "").strip()
            asset_type = row.get("Asset Type", "").strip().lower()

            # Only outgoing transfers initiated by the Safe itself.
            if not safe_addr or from_addr != safe_addr:
                continue
            # Skip WETH-unwrap burn (to == zero address).
            if not to_addr or to_addr == _ZERO_ADDRESS:
                continue
            if not amount_str:
                continue
            try:
                amount = float(amount_str)
            except ValueError:
                continue
            if amount <= 0:
                continue

            if asset_type == "native":
                transfers.append(
                    Transfer(
                        token_type="native",
                        token_address="",
                        receiver=to_addr,
                        amount=amount,
                    )
                )
            elif asset_type == "erc20":
                transfers.append(
                    Transfer(
                        token_type="erc20",
                        token_address=cow_token_address,
                        receiver=to_addr,
                        amount=amount,
                    )
                )

    return transfers


@dataclass(frozen=True)
class FeeSummary:
    """Protocol fee data from the Dune Fees export."""

    protocol_fee: float  # protocol_fee_in_native_token (net, after partner deductions)


def load_fee_summary(path: str) -> FeeSummary:
    """Load protocol fee summary from a Dune Fees CSV.

    The only column currently consumed is ``protocol_fee_in_native_token``,
    which is the net native-token amount the protocol retains after subtracting
    partner-fee payouts.
    """
    with open(path, newline="", encoding="utf-8") as f:
        rows = list(csv.DictReader(f))
    if not rows:
        raise ValueError(f"No data rows in {path}")
    value = rows[0].get("protocol_fee_in_native_token", "").strip()
    if not value:
        raise ValueError(f"Missing 'protocol_fee_in_native_token' in {path}")
    return FeeSummary(protocol_fee=float(value))


@dataclass(frozen=True)
class PartnerFee:
    """A single partner's fee data from the Dune partner-fees export.

    ``partner_fee_part`` is the native-token amount transferred directly to
    ``recipient``. ``cow_dao_partner_fee_part`` is that partner's contribution
    to the aggregate "partner fee tax" transfer sent to the protocol fee safe
    (all partners' shares are summed into a single transfer).
    """

    recipient: str
    app_code: str
    partner_fee_part: float
    cow_dao_partner_fee_part: float

    @classmethod
    def from_csv_row(cls, row: dict) -> "PartnerFee":
        """Parse a PartnerFee from a CSV DictReader row (or an equivalent Dune API row)."""
        return cls(
            recipient=row["partner_recipient"].strip().lower(),
            app_code=(row.get("app_code") or "").strip(),
            partner_fee_part=parse_amount(row.get("partner_fee_part")),
            cow_dao_partner_fee_part=parse_amount(row.get("cow_dao_partner_fee_part")),
        )


def load_partner_fees(path: str) -> list[PartnerFee]:
    """Load partner fees from a Dune partner-fees CSV."""
    with open(path, newline="", encoding="utf-8") as f:
        return [PartnerFee.from_csv_row(row) for row in csv.DictReader(f)]


_T = TypeVar("_T")


def _closest(items: list[_T], amount: float) -> _T:
    """The item (a Transfer or an overdraft entry) whose amount is closest to `amount`."""
    return min(items, key=lambda item: abs(getattr(item, "amount") - amount))


def amounts_match(actual: float, expected: float, tolerance: float) -> bool:
    """True if `actual` and `expected` differ by no more than `tolerance` (relative)."""
    diff = abs(actual - expected)
    largest = max(abs(actual), abs(expected))
    if largest == 0:
        return diff == 0
    return diff <= largest * tolerance


@dataclass
class Issue:
    """A single verification finding (error or warning)."""

    severity: str  # "error" or "warning"
    message: str

    def __str__(self) -> str:
        icon = "❌ ERROR" if self.severity == "error" else "⚠️  WARNING"
        return f"{icon}: {self.message}"


@dataclass
class SolverTotals:
    """Accumulated transfer totals for a single solver."""

    quote: float = 0.0
    native: float = 0.0
    solve: float = 0.0
    overdraft: float = 0.0


@dataclass
class ComparisonReport:  # pylint: disable=too-many-instance-attributes
    """Collects issues and totals produced by a comparison run."""

    issues: list[Issue] = field(default_factory=list)
    # Expected transfers that are missing because they are below the payout script's
    # minimum transfer amount (MIN_COW_TRANSFER / MIN_NATIVE_TRANSFER), so never sent.
    skipped_below_minimum: list[str] = field(default_factory=list)
    solver_totals: dict[str, SolverTotals] = field(default_factory=dict)
    totals: SolverTotals = field(default_factory=SolverTotals)
    unmatched_transfers: list[Transfer] = field(default_factory=list)
    # Fee amounts confirmed against a transfer. None means the check didn't run
    # because no Dune fee data was supplied; 0.0 means it ran and found nothing
    # (which, for a fee that was expected, also records an error).
    protocol_fee: Optional[float] = None
    partner_fees: Optional[float] = None
    partner_fee_tax: Optional[float] = None

    def issue(self, message: str, amount: float, threshold: float) -> None:
        """Record an error if ``amount`` exceeds ``threshold``, else a warning."""
        if amount > threshold:
            self.error(message)
        else:
            self.warning(message)

    def error(self, message: str) -> None:
        """Record an error-level issue."""
        self.issues.append(Issue("error", message))

    def warning(self, message: str) -> None:
        """Record a warning-level issue."""
        self.issues.append(Issue("warning", message))

    @property
    def errors(self) -> list[Issue]:
        """All error-level issues."""
        return [issue for issue in self.issues if issue.severity == "error"]

    @property
    def warnings(self) -> list[Issue]:
        """All warning-level issues."""
        return [issue for issue in self.issues if issue.severity == "warning"]

    @property
    def is_valid(self) -> bool:
        """True when no errors have been recorded."""
        return not self.errors


@dataclass
class _Expected:  # pylint: disable=too-many-instance-attributes
    """An expected transfer, as looked for by compare_safe_exports."""

    message: str  # reported when there is no transfer to the receivers at all
    description: str  # names the transfer when it was sent with a different amount
    receivers: tuple[str, ...]  # tried in order for an exact match
    amount: float
    token_type: str  # "erc20" (COW) or "native" (incl. wrapped native)
    pool: list[Transfer]  # the remaining transfers to look in; matches are removed
    threshold: float  # a missing transfer or difference above this is an error
    minimum: float  # the payout script does not send transfers below this
    on_found: Callable[[Transfer], None]  # called with an exactly matching transfer
    # called with a transfer with a different amount; None: the amount is not recorded
    on_mismatch: Optional[Callable[[Transfer], None]] = None


def compare(  # pylint: disable=too-many-arguments
    dune_rewards: list[DuneReward],
    transfers: list[Transfer],
    cow_token_address: str,
    *,
    cow_threshold: float = DEFAULT_COW_THRESHOLD,
    native_threshold: float = DEFAULT_NATIVE_THRESHOLD,
    tolerance: float = DEFAULT_TOLERANCE,
    protocol_fee: Optional[float] = None,
    protocol_fee_safe: Optional[str] = None,
    partner_fees: Optional[list[PartnerFee]] = None,
    overdraft_entries: Optional[list] = None,
) -> ComparisonReport:
    """Order-independent comparison of Dune rewards against a combined transfers list.

    Splits `transfers` by token_type and delegates to `compare_safe_exports`, which
    locates each expected transfer by (receiver, amount) rather than by position.
    """
    cow_transfers = [t for t in transfers if t.token_type == "erc20"]
    native_transfers = [t for t in transfers if t.token_type == "native"]
    return compare_safe_exports(
        dune_rewards,
        cow_transfers,
        native_transfers,
        cow_token_address,
        cow_threshold=cow_threshold,
        native_threshold=native_threshold,
        tolerance=tolerance,
        protocol_fee=protocol_fee,
        protocol_fee_safe=protocol_fee_safe,
        partner_fees=partner_fees,
        overdraft_entries=overdraft_entries,
    )


def compare_safe_exports(  # pylint: disable=too-many-arguments,too-many-locals,too-many-branches,too-many-statements
    dune_rewards: list[DuneReward],
    cow_transfers: list[Transfer],
    native_transfers: list[Transfer],
    cow_token_address: str,
    *,
    cow_threshold: float = DEFAULT_COW_THRESHOLD,
    native_threshold: float = DEFAULT_NATIVE_THRESHOLD,
    tolerance: float = DEFAULT_TOLERANCE,
    protocol_fee: Optional[float] = None,
    protocol_fee_safe: Optional[str] = None,
    partner_fees: Optional[list[PartnerFee]] = None,
    overdraft_entries: Optional[list] = None,
) -> ComparisonReport:
    """Set-based comparison using separate COW and native transfer lists.

    Transfers may appear in any order. Each expected solver transfer is
    located by (receiver, amount) in the respective list. ``compare()`` is a
    thin wrapper that splits a single combined transfers list into these two
    pools and delegates here.

    Protocol fee verification (optional):
        If both ``protocol_fee`` and ``protocol_fee_safe`` are provided, the
        function looks for a native transfer to ``protocol_fee_safe`` with
        amount ≈ ``protocol_fee`` (from the Dune Fees
        export) and verifies it.

    Partner fee verification (optional):
        If ``partner_fees`` is provided, each partner's ``partner_fee_part`` is
        matched against a native transfer to its ``recipient``, and the sum of
        every partner's ``cow_dao_partner_fee_part`` is matched against a
        single aggregate native transfer to ``protocol_fee_safe`` (the
        "partner fee tax").

    Overdraft verification (optional):
        If ``overdraft_entries`` (decoded `addOverdraft(account, amount)` calls)
        is provided, each Dune reward with a negative ``overdraft`` (i.e. the
        solver owes the protocol) is matched against an entry for its
        ``solver_address``.

    Every expected transfer with a positive amount is looked for, however
    small. Native expectations also match transfers in the wrapped native token,
    in which the payout script sends fees. Once all exact matching is done, each
    expected transfer that was not found is resolved:

    - below the payout script's minimum transfer (``MIN_COW_TRANSFER`` /
      ``MIN_NATIVE_TRANSFER``), it was never sent: it is recorded in
      ``report.skipped_below_minimum`` and not reported as an issue;
    - if a remaining transfer goes to the same receiver with a different amount,
      the two are reported together as one difference, an error if the
      difference exceeds the relevant threshold, else a warning;
    - otherwise it is missing: an error if its amount exceeds the relevant
      threshold (``native_threshold`` or ``cow_threshold``), else a warning.

    Overdrafts are resolved the same way, against entries for the same account.

    Unmatched transfers:
        After all of the above matching, remaining transfers land in
        ``report.unmatched_transfers``. Transfers to the ``protocol_fee_safe``
        address are labelled as "partner fee tax"; all others as generic
        unmatched. An unmatched transfer above the relevant threshold
        (``native_threshold`` or ``cow_threshold``) is an error; below it, a
        warning.
    """
    report = ComparisonReport()

    remaining_cow = list(cow_transfers)
    remaining_native = list(native_transfers)
    # Expected transfers without an exact match, resolved once all exact matching is done.
    missing: list[_Expected] = []

    def find_and_remove(
        pool: list[Transfer], receiver: str, amount: float
    ) -> Optional[Transfer]:
        for i, t in enumerate(pool):
            if t.receiver == receiver and amounts_match(t.amount, amount, tolerance):
                return pool.pop(i)
        return None

    def expect(expected: _Expected) -> None:
        """Match an expected transfer exactly, or queue it for `resolve_missing`."""
        for receiver in expected.receivers:
            t = find_and_remove(expected.pool, receiver, expected.amount)
            if t is not None:
                expected.on_found(t)
                return
        missing.append(expected)

    def resolve_missing() -> None:
        """Report expected transfers that had no exact match.

        Runs after all exact matching, so that a transfer with a different amount is only
        paired with an expected transfer once no other expected transfer matches it
        exactly (e.g. quote and solve rewards share a receiver).
        """
        for expected in missing:
            if expected.amount < expected.minimum:
                # The payout script never sends transfers this small.
                report.skipped_below_minimum.append(expected.message)
                continue
            candidates = [
                t
                for t in expected.pool
                if t.receiver in expected.receivers
                and t.token_type == expected.token_type
            ]
            if not candidates:
                report.issue(expected.message, expected.amount, expected.threshold)
                continue
            # A transfer to the same receiver with a different amount: report the
            # difference instead of a missing and an unmatched transfer.
            t = _closest(candidates, expected.amount)
            expected.pool.remove(t)
            difference = t.amount - expected.amount
            report.issue(
                f"{expected.description} to {t.receiver} is off by {difference:+.10g}: "
                f"expected {expected.amount}, sent {t.amount}",
                abs(difference),
                expected.threshold,
            )
            if expected.on_mismatch is not None:
                expected.on_mismatch(t)

    remaining_overdrafts = (
        list(overdraft_entries) if overdraft_entries is not None else None
    )
    missing_overdrafts: list[tuple[DuneReward, float]] = []

    def find_and_remove_overdraft(account: str, amount: float) -> Any:
        # Overdraft entries are duck-typed (an object with .account/.amount) rather
        # than a concrete type, to avoid compare_output_files.py depending on
        # decode_calldata.py's OverdraftEntry at module level (see overdraft_entries
        # on compare_safe_exports below).
        if remaining_overdrafts is None:
            return None
        for i, entry in enumerate(remaining_overdrafts):
            if entry.account == account and amounts_match(
                entry.amount, amount, tolerance
            ):
                return remaining_overdrafts.pop(i)
        return None

    def cow_reward_found(reward: DuneReward, kind: str) -> Callable[[Transfer], None]:
        def record(t: Transfer) -> None:
            if t.token_address != cow_token_address:
                report.error(
                    f"{reward.name}: {kind} reward uses token {t.token_address}, "
                    f"expected {cow_token_address}"
                )
            totals = report.solver_totals[reward.solver_name]
            if kind == "quote":
                totals.quote += t.amount
                report.totals.quote += t.amount
            else:
                totals.solve += t.amount
                report.totals.solve += t.amount

        return record

    def native_reward_found(reward: DuneReward) -> Callable[[Transfer], None]:
        def record(t: Transfer) -> None:
            if t.receiver != reward.reward_target:
                report.warning(
                    f"{reward.name}: native transfer sent to solver address "
                    f"{t.receiver}, not reward target {reward.reward_target}"
                )
            if t.is_wrapped_native:
                # The payout script pays solver rewards in the native token only.
                report.warning(
                    f"{reward.name}: native reward paid in wrapped native token "
                    f"{t.token_address}"
                )
            totals = report.solver_totals[reward.solver_name]
            totals.native += t.amount
            report.totals.native += t.amount

        return record

    for reward in dune_rewards:
        report.solver_totals.setdefault(reward.solver_name, SolverTotals())

        # 1. Quote reward (COW).
        if reward.quote_reward > 0:
            record_quote = cow_reward_found(reward, "quote")
            expect(
                _Expected(
                    message=f"{reward.name}: missing quote reward transfer of "
                    f"{reward.quote_reward} COW to {reward.reward_target}",
                    description=f"{reward.name}: quote reward transfer (COW)",
                    receivers=(reward.reward_target,),
                    amount=reward.quote_reward,
                    token_type="erc20",
                    pool=remaining_cow,
                    threshold=cow_threshold,
                    minimum=MIN_COW_TRANSFER,
                    on_found=record_quote,
                    on_mismatch=record_quote,
                )
            )

        # 2. Native transfer, to the reward target or else to the solver address.
        if reward.native_token_transfer > 0:
            record_native = native_reward_found(reward)
            expect(
                _Expected(
                    message=f"{reward.name}: missing native transfer of "
                    f"{reward.native_token_transfer} to {reward.reward_target}",
                    description=f"{reward.name}: native transfer",
                    receivers=(reward.reward_target, reward.solver_address),
                    amount=reward.native_token_transfer,
                    token_type="native",
                    pool=remaining_native,
                    threshold=native_threshold,
                    minimum=MIN_NATIVE_TRANSFER,
                    on_found=record_native,
                    on_mismatch=record_native,
                )
            )

        # 3. Solve reward (COW).
        if reward.cow_transfer > 0:
            record_solve = cow_reward_found(reward, "solve")
            expect(
                _Expected(
                    message=f"{reward.name}: missing solve reward transfer of "
                    f"{reward.cow_transfer} COW to {reward.reward_target}",
                    description=f"{reward.name}: solve reward transfer (COW)",
                    receivers=(reward.reward_target,),
                    amount=reward.cow_transfer,
                    token_type="erc20",
                    pool=remaining_cow,
                    threshold=cow_threshold,
                    minimum=MIN_COW_TRANSFER,
                    on_found=record_solve,
                    on_mismatch=record_solve,
                )
            )

        # 4. Overdraft (solver owes the protocol; reward.overdraft is negative).
        if remaining_overdrafts is not None and reward.overdraft < 0:
            expected_amount = -reward.overdraft
            entry = find_and_remove_overdraft(reward.solver_address, expected_amount)
            if entry is None:
                missing_overdrafts.append((reward, expected_amount))
            else:
                report.solver_totals[reward.solver_name].overdraft += entry.amount
                report.totals.overdraft += entry.amount

    # Overdrafts without an exact match: report a differing entry for the same account
    # as a difference, everything else as missing or unmatched.
    for reward, expected_amount in missing_overdrafts:
        assert remaining_overdrafts is not None
        same_account = [
            e for e in remaining_overdrafts if e.account == reward.solver_address
        ]
        if not same_account:
            report.issue(
                f"{reward.name}: missing overdraft transaction of "
                f"{expected_amount} for {reward.solver_address}",
                expected_amount,
                native_threshold,
            )
            continue
        entry = _closest(same_account, expected_amount)
        remaining_overdrafts.remove(entry)
        difference = entry.amount - expected_amount
        report.issue(
            f"{reward.name}: overdraft transaction for {reward.solver_address} is off "
            f"by {difference:+.10g}: expected {expected_amount}, sent {entry.amount}",
            abs(difference),
            native_threshold,
        )
        report.solver_totals[reward.solver_name].overdraft += entry.amount
        report.totals.overdraft += entry.amount

    if remaining_overdrafts:
        for entry in remaining_overdrafts:
            report.issue(
                f"Unmatched overdraft transaction of {entry.amount} for {entry.account}",
                entry.amount,
                native_threshold,
            )

    # Protocol fee verification (optional).
    protocol_fee_safe_lower = protocol_fee_safe.lower() if protocol_fee_safe else None
    if protocol_fee is not None and protocol_fee_safe_lower:
        report.protocol_fee = 0.0

        def record_protocol_fee(t: Transfer) -> None:
            report.protocol_fee = t.amount

        expect(
            _Expected(
                message=f"Missing protocol fee transfer of {protocol_fee} native to "
                f"{protocol_fee_safe_lower}",
                description="Protocol fee transfer",
                receivers=(protocol_fee_safe_lower,),
                amount=protocol_fee,
                token_type="native",
                pool=remaining_native,
                threshold=native_threshold,
                minimum=MIN_NATIVE_TRANSFER,
                # A differing fee is reported, but not confirmed.
                on_found=record_protocol_fee,
            )
        )

    # Partner fee verification (optional).
    if partner_fees:
        report.partner_fees = 0.0
        report.partner_fee_tax = 0.0

        def record_partner_fee(t: Transfer) -> None:
            assert report.partner_fees is not None
            report.partner_fees += t.amount

        def record_partner_fee_tax(t: Transfer) -> None:
            report.partner_fee_tax = t.amount

        for pf in partner_fees:
            if pf.partner_fee_part > 0:
                expect(
                    _Expected(
                        message=f"Missing partner fee transfer of {pf.partner_fee_part} "
                        f"native to {pf.recipient} ({pf.app_code})",
                        description=f"Partner fee transfer ({pf.app_code})",
                        receivers=(pf.recipient,),
                        amount=pf.partner_fee_part,
                        token_type="native",
                        pool=remaining_native,
                        threshold=native_threshold,
                        minimum=MIN_NATIVE_TRANSFER,
                        on_found=record_partner_fee,
                    )
                )

        total_partner_tax = sum(pf.cow_dao_partner_fee_part for pf in partner_fees)
        if protocol_fee_safe_lower and total_partner_tax > 0:
            expect(
                _Expected(
                    message=f"Missing aggregate partner fee tax transfer of "
                    f"{total_partner_tax} native to {protocol_fee_safe_lower}",
                    description="Aggregate partner fee tax transfer",
                    receivers=(protocol_fee_safe_lower,),
                    amount=total_partner_tax,
                    token_type="native",
                    pool=remaining_native,
                    threshold=native_threshold,
                    minimum=MIN_NATIVE_TRANSFER,
                    on_found=record_partner_fee_tax,
                )
            )

    resolve_missing()

    # Any transfers not matched to a Dune entry, protocol fee, or partner fee.
    report.unmatched_transfers = remaining_cow + remaining_native
    for transfer in report.unmatched_transfers:
        if (
            transfer.token_type == "erc20"
            and transfer.token_address != cow_token_address
        ):
            report.error(
                f"Unmatched transfer uses token {transfer.token_address}, expected "
                f"the COW token {cow_token_address}: {transfer}"
            )
            continue

        threshold = (
            cow_threshold if transfer.token_type == "erc20" else native_threshold
        )

        if protocol_fee_safe_lower and transfer.receiver == protocol_fee_safe_lower:
            message = (
                f"Unverified fee transfer to protocol safe "
                f"(likely partner fee tax): {transfer}"
            )
        else:
            message = f"Unmatched transfer, not verified against Dune data: {transfer}"

        report.issue(message, transfer.amount, threshold)

    return report


def print_fee_confirmation(report: ComparisonReport) -> None:
    """Print the fee transfers that were confirmed against the Dune fee data.

    Each line mirrors one of the "Payment breakdown" fee lines the payouts script
    posts to Slack when it proposes the transactions, so the two can be read
    side by side. A fee whose check didn't run is reported as such rather than
    silently omitted - an unchecked fee is not a verified one.
    """
    labelled = (
        ("Protocol fees (excl. partner)", report.protocol_fee),
        ("Partner fees (after tax)", report.partner_fees),
        ("Partner fees tax", report.partner_fee_tax),
    )
    print("\U0001f9fe Fee transfers confirmed against Dune:")
    for label, amount in labelled:
        if amount is None:
            print(f"   {label + ':':<31} not checked (no Dune fee data)")
        else:
            print(f"   {label + ':':<31} {amount:,.4f} ETH \u2713")
    print()


def print_report(report: ComparisonReport) -> None:
    """Print issues and per-solver totals to stdout."""
    for issue in report.issues:
        print(issue)

    if report.skipped_below_minimum:
        print()
        print(
            f"\u2139\ufe0f  Not checked, below the payout script's minimum transfer "
            f"({MIN_COW_TRANSFER:g} COW / {MIN_NATIVE_TRANSFER:g} native), so never sent:"
        )
        for message in report.skipped_below_minimum:
            print(f"   {message}")

    print()
    print("\U0001f4dd Summary:")
    for name in sorted(report.solver_totals):
        totals = report.solver_totals[name]
        print(f"   ☊ {name}")
        print(
            f"   quote: {totals.quote:,.2f}, native: {totals.native:,.4f}, "
            f"solve: {totals.solve:,.2f}"
        )

    print()
    print(f"   Total quote rewards:   {report.totals.quote:,.2f} COW")
    print(f"   Total native transfer: {report.totals.native:,.4f} ETH")
    print(f"   Total solve rewards:   {report.totals.solve:,.2f} COW")
    if report.totals.overdraft:
        print(f"   Total overdraft:       {report.totals.overdraft:,.4f} ETH")
    print()
    print_fee_confirmation(report)

    if report.is_valid:
        print("✅ Transaction is valid: ok to sign")
    else:
        print("\U0001f6ab Transaction is NOT valid: do not sign")


DEFAULT_PROTOCOL_FEE_SAFE = "0x22af3D38E50ddedeb7C47f36faB321eC3Bb72A76"


def parse_args(argv: Optional[list[str]] = None) -> argparse.Namespace:
    """Parse CLI arguments."""
    parser = argparse.ArgumentParser(
        description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter
    )
    parser.add_argument(
        "dune_csv",
        nargs="?",
        help=(
            "Path to the Dune solver-rewards CSV export. Omit and pass --start "
            "to fetch it (and the fees/partner-fees data) directly from Dune instead."
        ),
    )

    mode = parser.add_mutually_exclusive_group()
    mode.add_argument(
        "transfers_csv",
        nargs="?",
        help=(
            "Path to a combined transfers CSV (token_type/token_address/receiver/amount). "
            "Mutually exclusive with --cow-safe-csv / --cow-transfers-calldata(-file)."
        ),
    )
    mode.add_argument(
        "--cow-safe-csv",
        metavar="PATH",
        help="Safe transaction-export CSV for COW transfers (mainnet Safe).",
    )
    mode.add_argument(
        "--cow-transfers-calldata",
        metavar="HEX_OR_JSON",
        help=(
            "Raw multisend calldata (or the Safe tx JSON containing it) for the "
            "COW-transfer transaction, copied from the Safe UI."
        ),
    )
    mode.add_argument(
        "--cow-transfers-calldata-file",
        metavar="PATH",
        help="Same as --cow-transfers-calldata, read from a file instead.",
    )

    native_mode = parser.add_mutually_exclusive_group()
    native_mode.add_argument(
        "--native-safe-csv",
        metavar="PATH",
        help=(
            "Safe transaction-export CSV for native transfers (network Safe). "
            "Required when --cow-safe-csv / --cow-transfers-calldata(-file) is used."
        ),
    )
    native_mode.add_argument(
        "--native-transfers-calldata",
        metavar="HEX_OR_JSON",
        help="Raw multisend calldata (or Safe tx JSON) for the native-transfer transaction.",
    )
    native_mode.add_argument(
        "--native-transfers-calldata-file",
        metavar="PATH",
        help="Same as --native-transfers-calldata, read from a file instead.",
    )

    overdraft_mode = parser.add_mutually_exclusive_group()
    overdraft_mode.add_argument(
        "--overdraft-calldata",
        metavar="HEX_OR_JSON",
        help=(
            "Raw multisend calldata (or Safe tx JSON) for the overdrafts transaction. "
            "When provided, each Dune reward's overdraft is verified against it."
        ),
    )
    overdraft_mode.add_argument(
        "--overdraft-calldata-file",
        metavar="PATH",
        help="Same as --overdraft-calldata, read from a file instead.",
    )

    parser.add_argument(
        "--out-dir",
        metavar="DIR",
        default=".",
        help=(
            "Directory to write CSVs decoded from any --*-calldata(-file) inputs "
            "(default: current directory)."
        ),
    )
    parser.add_argument(
        "--start",
        metavar="YYYY-MM-DD",
        help=(
            "Accounting period start date. When provided, the solver-rewards, "
            "protocol-fee, and partner-fees data are fetched directly from Dune "
            "instead of requiring dune_csv/--fees-csv/--partner-fees-csv."
        ),
    )
    parser.add_argument(
        "-n",
        "--network",
        choices=NETWORKS,
        required=False,
        default="mainnet",
        help="Network the rewards are for (used for Dune fetching and Safe-export decoding)",
    )
    parser.add_argument(
        "--cow-threshold",
        type=float,
        default=DEFAULT_COW_THRESHOLD,
        help=(
            "COW amount above which a missing or unmatched transfer is an error "
            "rather than a warning (default: %(default)s)"
        ),
    )
    parser.add_argument(
        "--native-threshold",
        type=float,
        default=DEFAULT_NATIVE_THRESHOLD,
        help=(
            "Native amount above which a missing or unmatched transfer is an "
            "error rather than a warning (default: %(default)s)"
        ),
    )
    parser.add_argument(
        "--tolerance",
        type=float,
        default=DEFAULT_TOLERANCE,
        help=(
            "Max relative difference allowed between Dune and "
            "transfer amounts (default: %(default)s)"
        ),
    )
    parser.add_argument(
        "--fees-csv",
        metavar="PATH",
        help=(
            "Dune weekly cost-coverage CSV export, whose protocol_fee_in_native_token "
            "value is matched against a transfer to --protocol-fee-safe and verified. "
            "--start fetches this automatically; pass this to override it."
        ),
    )
    parser.add_argument(
        "--partner-fees-csv",
        metavar="PATH",
        help=(
            "Dune partner-fees CSV export: each partner's fee and its share of the "
            "partner fee tax are verified against transfers to the partner and to "
            "--protocol-fee-safe. --start fetches this automatically; pass this to "
            "override it."
        ),
    )
    parser.add_argument(
        "--protocol-fee-safe",
        metavar="ADDR",
        default=DEFAULT_PROTOCOL_FEE_SAFE,
        help=(
            "Address of the protocol fee safe (DAO wallet). Transfers to this "
            "address are classified as protocol fee or partner fee tax "
            "(default: %(default)s)."
        ),
    )
    return parser.parse_args(argv)


def _read_calldata_arg(
    inline: Optional[str], file_path: Optional[str]
) -> Optional[str]:
    """Returns pasted calldata from either an inline CLI value or a file."""
    if file_path:
        with open(file_path, encoding="utf-8") as f:
            return f.read()
    return inline


def _resolve_cow_transfers(
    args: argparse.Namespace, cow_token_address: str
) -> Optional[list[Transfer]]:
    """Resolves COW transfers from calldata or a Safe-export CSV, whichever was given."""
    # pylint: disable=import-outside-toplevel
    calldata = _read_calldata_arg(
        args.cow_transfers_calldata, args.cow_transfers_calldata_file
    )
    if calldata:
        from src.verification.decode_calldata import (
            decode_transfers,
            write_transfers_csv,
        )

        transfers = decode_transfers(calldata, "erc20", cow_token_address)
        write_transfers_csv(
            transfers,
            os.path.join(args.out_dir, f"decoded-cow-transfers-{args.network}.csv"),
        )
        return transfers
    if args.cow_safe_csv:
        return load_safe_transfers(args.cow_safe_csv, cow_token_address)
    return None


def _resolve_native_transfers(
    args: argparse.Namespace, cow_token_address: str
) -> Optional[list[Transfer]]:
    """Resolves native transfers from calldata or a Safe-export CSV, whichever was given."""
    # pylint: disable=import-outside-toplevel
    calldata = _read_calldata_arg(
        args.native_transfers_calldata, args.native_transfers_calldata_file
    )
    if calldata:
        from src.verification.decode_calldata import (
            decode_transfers,
            write_transfers_csv,
        )

        transfers = decode_transfers(
            calldata,
            "native",
            cow_token_address,
            WRAPPED_NATIVE_TOKEN_ADDRESSES[args.network],
        )
        write_transfers_csv(
            transfers,
            os.path.join(args.out_dir, f"decoded-native-transfers-{args.network}.csv"),
        )
        return transfers
    if args.native_safe_csv:
        return load_safe_transfers(args.native_safe_csv, cow_token_address)
    return None


def _resolve_overdraft_entries(args: argparse.Namespace) -> Optional[list]:
    """Decodes the overdrafts calldata, if any was given."""
    # pylint: disable=import-outside-toplevel
    calldata = _read_calldata_arg(args.overdraft_calldata, args.overdraft_calldata_file)
    if not calldata:
        return None
    from src.verification.decode_calldata import decode_overdrafts, write_overdrafts_csv

    entries = decode_overdrafts(calldata)
    write_overdrafts_csv(
        entries, os.path.join(args.out_dir, f"decoded-overdrafts-{args.network}.csv")
    )
    return entries


def main(  # pylint: disable=too-many-branches,too-many-locals,cyclic-import
    argv: Optional[list[str]] = None,
) -> int:
    """Entry point: parse args, run comparison, print report."""
    args = parse_args(argv)
    cow_token_address = COW_TOKEN_ADDRESS

    # Decode pasted calldata before the (slow) Dune fetch, so bad input fails fast.
    try:
        cow_transfers = _resolve_cow_transfers(args, cow_token_address)
        native_transfers = _resolve_native_transfers(args, cow_token_address)
        overdraft_entries = _resolve_overdraft_entries(args)
    except ValueError as err:
        print(f"error: {err}", file=sys.stderr)
        return 2

    if args.start:
        if args.dune_csv:
            print("error: dune_csv and --start are mutually exclusive", file=sys.stderr)
            return 2
        # Local import: auto-fetch mode is the only path that needs dune_client/src.config.
        from src.config import Network  # pylint: disable=import-outside-toplevel
        from src.models.accounting_period import (  # pylint: disable=import-outside-toplevel
            AccountingPeriod,
        )
        from src.verification.dune_fetch import (  # pylint: disable=import-outside-toplevel
            fetch_fee_summary,
            fetch_partner_fees,
            fetch_solver_rewards,
            make_dune_client,
        )

        period = AccountingPeriod(args.start)
        network = Network(args.network)
        dune = make_dune_client()
        dune_rewards = fetch_solver_rewards(dune, network, period)
        fee_summary: Optional[FeeSummary] = fetch_fee_summary(dune, network, period)
        partner_fees: Optional[list[PartnerFee]] = fetch_partner_fees(
            dune, network, period
        )
    else:
        if not args.dune_csv:
            print(
                "error: dune_csv is required unless --start is given", file=sys.stderr
            )
            return 2
        dune_rewards = load_dune_rewards(args.dune_csv)
        fee_summary = None
        partner_fees = None

    if args.fees_csv:
        fee_summary = load_fee_summary(args.fees_csv)
    if args.partner_fees_csv:
        partner_fees = load_partner_fees(args.partner_fees_csv)

    kwargs: dict = {
        "cow_token_address": cow_token_address,
        "cow_threshold": args.cow_threshold,
        "native_threshold": args.native_threshold,
        "tolerance": args.tolerance,
        "partner_fees": partner_fees,
    }
    if fee_summary is not None:
        kwargs["protocol_fee"] = fee_summary.protocol_fee
        kwargs["protocol_fee_safe"] = args.protocol_fee_safe

    if args.transfers_csv:
        if cow_transfers is not None or native_transfers is not None:
            print(
                "error: transfers_csv is mutually exclusive with Safe-export/calldata "
                "inputs",
                file=sys.stderr,
            )
            return 2
        transfers = load_transfers(args.transfers_csv)
        report = compare(dune_rewards, transfers, **kwargs)
    else:
        if cow_transfers is None or native_transfers is None:
            print(
                "error: provide transfers_csv, or both COW and native transfer inputs "
                "(--cow-safe-csv/--native-safe-csv or the matching "
                "--*-calldata(-file) options)",
                file=sys.stderr,
            )
            return 2
        report = compare_safe_exports(
            dune_rewards,
            cow_transfers,
            native_transfers,
            overdraft_entries=overdraft_entries,
            **kwargs,
        )

    print_report(report)

    return 0 if report.is_valid else 1


if __name__ == "__main__":
    sys.exit(main())
