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
otherwise. An unmatched Safe transfer above the native/COW threshold is an
error; below it, a warning.
"""

from __future__ import annotations

import argparse
import csv
import os
import sys
from dataclasses import dataclass, field
from typing import Any, Optional

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

DEFAULT_COW_THRESHOLD = 1.0  # Don't expect a transfer for COW rewards below this.
DEFAULT_NATIVE_THRESHOLD = (
    0.001  # Don't expect a transfer for native rewards below this.
)
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

    def __str__(self) -> str:
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
class ComparisonReport:
    """Collects issues and totals produced by a comparison run."""

    issues: list[Issue] = field(default_factory=list)
    solver_totals: dict[str, SolverTotals] = field(default_factory=dict)
    totals: SolverTotals = field(default_factory=SolverTotals)
    unmatched_transfers: list[Transfer] = field(default_factory=list)

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
        export) and verifies it.  A missing match is an error.

    Partner fee verification (optional):
        If ``partner_fees`` is provided, each partner's ``partner_fee_part`` is
        matched against a native transfer to its ``recipient``, and the sum of
        every partner's ``cow_dao_partner_fee_part`` is matched against a
        single aggregate native transfer to ``protocol_fee_safe`` (the
        "partner fee tax"). A missing match for either is an error.

    Overdraft verification (optional):
        If ``overdraft_entries`` (decoded `addOverdraft(account, amount)` calls)
        is provided, each Dune reward with a negative ``overdraft`` (i.e. the
        solver owes the protocol) is matched against an entry for its
        ``solver_address``. A missing match is an error.

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

    def find_and_remove(
        pool: list[Transfer], receiver: str, amount: float
    ) -> Optional[Transfer]:
        for i, t in enumerate(pool):
            if t.receiver == receiver and amounts_match(t.amount, amount, tolerance):
                return pool.pop(i)
        return None

    remaining_overdrafts = (
        list(overdraft_entries) if overdraft_entries is not None else None
    )

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

    for reward in dune_rewards:
        totals = report.solver_totals.setdefault(reward.solver_name, SolverTotals())

        # 1. Quote reward (COW).
        if reward.quote_reward > cow_threshold:
            t = find_and_remove(
                remaining_cow, reward.reward_target, reward.quote_reward
            )
            if t is None:
                report.error(
                    f"{reward.name}: missing quote reward transfer of "
                    f"{reward.quote_reward} COW to {reward.reward_target}"
                )
            else:
                if t.token_address != cow_token_address:
                    report.error(
                        f"{reward.name}: quote reward uses token {t.token_address}, "
                        f"expected {cow_token_address}"
                    )
                totals.quote += t.amount
                report.totals.quote += t.amount

        # 2. Native transfer.
        if reward.native_token_transfer > native_threshold:
            t = find_and_remove(
                remaining_native, reward.reward_target, reward.native_token_transfer
            )
            sent_to_solver = False
            if t is None:
                t = find_and_remove(
                    remaining_native,
                    reward.solver_address,
                    reward.native_token_transfer,
                )
                if t is not None:
                    sent_to_solver = True
            if t is None:
                report.error(
                    f"{reward.name}: missing native transfer of "
                    f"{reward.native_token_transfer} (threshold {native_threshold})"
                )
            else:
                if sent_to_solver:
                    report.warning(
                        f"{reward.name}: native transfer sent to solver address "
                        f"{t.receiver}, not reward target {reward.reward_target}"
                    )
                totals.native += t.amount
                report.totals.native += t.amount

        # 3. Solve reward (COW).
        if reward.cow_transfer > cow_threshold:
            t = find_and_remove(
                remaining_cow, reward.reward_target, reward.cow_transfer
            )
            if t is None:
                report.error(
                    f"{reward.name}: missing solve reward transfer of "
                    f"{reward.cow_transfer} COW to {reward.reward_target}"
                )
            else:
                if t.token_address != cow_token_address:
                    report.error(
                        f"{reward.name}: solve reward uses token {t.token_address}, "
                        f"expected {cow_token_address}"
                    )
                totals.solve += t.amount
                report.totals.solve += t.amount

        # 4. Overdraft (solver owes the protocol; reward.overdraft is negative).
        if remaining_overdrafts is not None and reward.overdraft < -native_threshold:
            expected_amount = -reward.overdraft
            entry = find_and_remove_overdraft(reward.solver_address, expected_amount)
            if entry is None:
                report.error(
                    f"{reward.name}: missing overdraft transaction of "
                    f"{expected_amount} for {reward.solver_address}"
                )
            else:
                totals.overdraft += entry.amount
                report.totals.overdraft += entry.amount

    if remaining_overdrafts:
        for entry in remaining_overdrafts:
            message = (
                f"Unmatched overdraft transaction of {entry.amount} for {entry.account}"
            )
            if entry.amount > native_threshold:
                report.error(message)
            else:
                report.warning(message)

    # Protocol fee verification (optional).
    protocol_fee_safe_lower = protocol_fee_safe.lower() if protocol_fee_safe else None
    if protocol_fee is not None and protocol_fee_safe_lower:
        t = find_and_remove(remaining_native, protocol_fee_safe_lower, protocol_fee)
        if t is None:
            report.error(
                f"Missing protocol fee transfer of {protocol_fee} native to "
                f"{protocol_fee_safe_lower}"
            )

    # Partner fee verification (optional).
    if partner_fees:
        for pf in partner_fees:
            if pf.partner_fee_part > native_threshold:
                t = find_and_remove(remaining_native, pf.recipient, pf.partner_fee_part)
                if t is None:
                    report.error(
                        f"Missing partner fee transfer of {pf.partner_fee_part} native "
                        f"to {pf.recipient} ({pf.app_code})"
                    )

        total_partner_tax = sum(pf.cow_dao_partner_fee_part for pf in partner_fees)
        if protocol_fee_safe_lower and total_partner_tax > native_threshold:
            t = find_and_remove(
                remaining_native, protocol_fee_safe_lower, total_partner_tax
            )
            if t is None:
                report.error(
                    f"Missing aggregate partner fee tax transfer of {total_partner_tax} "
                    f"native to {protocol_fee_safe_lower}"
                )

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
        is_error = transfer.amount > threshold

        if protocol_fee_safe_lower and transfer.receiver == protocol_fee_safe_lower:
            message = (
                f"Unverified fee transfer to protocol safe "
                f"(likely partner fee tax): {transfer}"
            )
        else:
            message = f"Unmatched transfer, not verified against Dune data: {transfer}"

        if is_error:
            report.error(message)
        else:
            report.warning(message)

    return report


def print_report(report: ComparisonReport) -> None:
    """Print issues and per-solver totals to stdout."""
    for issue in report.issues:
        print(issue)

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
        help="Minimum COW reward that must be reflected as a transfer (default: %(default)s)",
    )
    parser.add_argument(
        "--native-threshold",
        type=float,
        default=DEFAULT_NATIVE_THRESHOLD,
        help=(
            "Minimum native amount that must be reflected as a transfer, and the "
            "cutoff above which an unmatched transfer is an error rather than a "
            "warning (default: %(default)s)"
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
            "Dune Fees CSV export. When provided (or fetched via --start), the "
            "protocol_fee_in_native_token value is matched against a transfer "
            "to --protocol-fee-safe and verified."
        ),
    )
    parser.add_argument(
        "--partner-fees-csv",
        metavar="PATH",
        help=(
            "Dune partner-fees CSV export. When provided (or fetched via --start), "
            "each partner's fee and its share of the partner fee tax are verified "
            "against transfers to the partner and to --protocol-fee-safe."
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

        transfers = decode_transfers(calldata, "native", cow_token_address)
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
            fetch_partner_fees,
            fetch_solver_rewards_and_fees,
            make_dune_client,
        )

        period = AccountingPeriod(args.start)
        network = Network(args.network)
        dune = make_dune_client()
        dune_rewards, fee_summary = fetch_solver_rewards_and_fees(dune, network, period)
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

    cow_transfers = _resolve_cow_transfers(args, cow_token_address)
    native_transfers = _resolve_native_transfers(args, cow_token_address)

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
        overdraft_entries = _resolve_overdraft_entries(args)
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
