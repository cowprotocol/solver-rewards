#!/usr/bin/env python3
"""Verify that solver-rewards transfers match the rewards reported by Dune.

Two comparison modes are available:

MODE 1 — Combined transfers CSV (original format):
    Accepts a single transfers CSV with columns: token_type, token_address,
    receiver, amount.  Rows must appear in the same order the rewards script
    emits them (quote COW → native → solve COW, sorted by solver address).

    Usage:
        python3 compare_output_files.py DUNE_CSV TRANSFERS_CSV --network arbitrum

MODE 2 — Safe transaction export CSVs (new format):
    Accepts two Safe transaction-export CSVs (one from the mainnet COW Safe,
    one from the network native Safe).  Order does not matter; each expected
    transfer is located by (receiver, amount) across the whole file.  This
    mode also verifies that every row in each Safe CSV can be traced back to
    a Dune entry or is flagged as an unmatched (fee/partner) transfer.

    Usage:
        python3 compare_output_files.py DUNE_CSV \\
            --cow-safe-csv MAINNET_SAFE.csv \\
            --native-safe-csv NETWORK_SAFE.csv \\
            --network arbitrum

Safe CSV columns (transaction export format):
    Nonce, Safe Address, From Address, To Address, Transaction Hash,
    Contract Address, Amount, Asset Type, Asset Symbol, ...

The Dune CSV must contain at minimum:
    name, solver_address, reward_target, quote_reward,
    native_token_transfer, cow_transfer

Exit status is 0 if no errors were found (warnings are still reported), and 1
otherwise.
"""

from __future__ import annotations

import argparse
import csv
import sys
from dataclasses import dataclass, field
from typing import Optional

# COW token contract address per network (all lower-case).
# TODO: add rest of the networks
COW_TOKEN_ADDRESSES = {
    "arbitrum": "0xcb8b5cd20bdcaea9a010ac1f8d835824f5c87a04",
    "base": "0xc694a91e6b071bf030a18bd3053a7fe09b6dae69",
    "gnosis": "0x177127622c4a00f3d409773c674621c441bc8b35",
    "mainnet": "0xdef1ca1fb7fbcdc777520aa7f396b4e015f497ab",
}

DEFAULT_COW_THRESHOLD = 1.0  # Don't expect a transfer for COW rewards below this.
DEFAULT_NATIVE_THRESHOLD = (
    0.001  # Don't expect a transfer for native rewards below this.
)
DEFAULT_TOLERANCE = (
    0.0001  # Max relative difference allowed between Dune and transfer amounts.
)


@dataclass(frozen=True)
class DuneReward:
    """A single solver's reward data from the Dune export."""

    name: str
    solver_address: str
    reward_target: str
    quote_reward: float
    native_token_transfer: float
    cow_transfer: float

    @property
    def solver_name(self) -> str:
        """The solver's name without its "prod-"/"barn-" environment prefix."""
        _, _, rest = self.name.partition("-")
        return rest or self.name

    @classmethod
    def from_csv_row(cls, row: dict) -> "DuneReward":
        """Parse a DuneReward from a CSV DictReader row."""

        def amount(key: str) -> float:
            value = row[key].strip()
            return float(value) if value else 0.0

        return cls(
            name=row["name"],
            solver_address=row["solver_address"].strip().lower(),
            reward_target=row["reward_target"].strip().lower(),
            quote_reward=amount("quote_reward"),
            native_token_transfer=amount("native_token_transfer"),
            cow_transfer=amount("cow_transfer"),
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


def _check_cow_reward(  # pylint: disable=too-many-arguments
    report: ComparisonReport,
    reward: DuneReward,
    transfer: Transfer,
    expected_amount: float,
    label: str,
    *,
    cow_token_address: str,
    tolerance: float,
) -> None:
    """Validate a single COW reward transfer against the Dune expectation."""
    if transfer.token_type != "erc20":
        report.error(
            f"{reward.name}: expected a {label} transfer of {expected_amount} COW "
            f"but found a {transfer.token_type} transfer instead ({transfer})"
        )
        return

    if transfer.token_address != cow_token_address:
        report.error(
            f"{reward.name}: {label} transfer uses token {transfer.token_address}, "
            f"expected the COW token {cow_token_address}"
        )

    if transfer.receiver != reward.reward_target:
        report.error(
            f"{reward.name}: {label} receiver {transfer.receiver} does not match "
            f"reward target {reward.reward_target}"
        )

    if not amounts_match(transfer.amount, expected_amount, tolerance):
        report.error(
            f"{reward.name}: {label} amount {transfer.amount} does not match "
            f"Dune-reported {expected_amount} (tolerance {tolerance:.4%})"
        )


def compare(  # pylint: disable=too-many-arguments,too-many-branches
    dune_rewards: list[DuneReward],
    transfers: list[Transfer],
    cow_token_address: str,
    *,
    cow_threshold: float = DEFAULT_COW_THRESHOLD,
    native_threshold: float = DEFAULT_NATIVE_THRESHOLD,
    tolerance: float = DEFAULT_TOLERANCE,
) -> ComparisonReport:
    """Order-dependent comparison of Dune rewards against a combined transfers list."""
    report = ComparisonReport()

    index = 0

    def peek() -> Optional[Transfer]:
        return transfers[index] if index < len(transfers) else None

    def take() -> Optional[Transfer]:
        nonlocal index
        transfer = peek()
        if transfer is not None:
            index += 1
        return transfer

    for reward in dune_rewards:
        totals = report.solver_totals.setdefault(reward.solver_name, SolverTotals())

        # 1. Quote reward, paid in COW.
        if reward.quote_reward > cow_threshold:
            transfer = take()
            if transfer is None:
                report.error(
                    f"{reward.name}: missing quote reward transfer of "
                    f"{reward.quote_reward} COW"
                )
            else:
                _check_cow_reward(
                    report,
                    reward,
                    transfer,
                    reward.quote_reward,
                    "quote reward",
                    cow_token_address=cow_token_address,
                    tolerance=tolerance,
                )
                totals.quote += transfer.amount
                report.totals.quote += transfer.amount

        # 2. Native token transfer.
        next_transfer = peek()
        if (
            next_transfer is not None
            and next_transfer.token_type == "native"
            and reward.native_token_transfer
        ):
            transfer = take()
            assert transfer is not None
            if not amounts_match(
                transfer.amount, reward.native_token_transfer, tolerance
            ):
                report.error(
                    f"{reward.name}: native transfer amount {transfer.amount} does not "
                    f"match Dune-reported {reward.native_token_transfer} "
                    f"(tolerance {tolerance:.4%})"
                )
            if transfer.receiver != reward.reward_target:
                if transfer.receiver != reward.solver_address:
                    report.error(
                        f"{reward.name}: native transfer sent to unexpected address "
                        f"{transfer.receiver} (expected reward target "
                        f"{reward.reward_target})"
                    )
                else:
                    report.warning(
                        f"{reward.name}: native transfer sent to solver address "
                        f"{transfer.receiver}, not reward target {reward.reward_target}"
                    )
            totals.native += transfer.amount
            report.totals.native += transfer.amount
        elif reward.native_token_transfer > native_threshold:
            report.error(
                f"{reward.name}: missing native transfer of "
                f"{reward.native_token_transfer} (threshold {native_threshold})"
            )

        # 3. Solve reward, paid in COW.
        if reward.cow_transfer > cow_threshold:
            transfer = take()
            if transfer is None:
                report.error(
                    f"{reward.name}: missing solve reward transfer of "
                    f"{reward.cow_transfer} COW"
                )
            else:
                _check_cow_reward(
                    report,
                    reward,
                    transfer,
                    reward.cow_transfer,
                    "solve reward",
                    cow_token_address=cow_token_address,
                    tolerance=tolerance,
                )
                totals.solve += transfer.amount
                report.totals.solve += transfer.amount

    # Anything left over wasn't matched against a Dune reward at all.
    report.unmatched_transfers = transfers[index:]
    for transfer in report.unmatched_transfers:
        if (
            transfer.token_type == "erc20"
            and transfer.token_address != cow_token_address
        ):
            report.error(
                f"Unmatched transfer uses token {transfer.token_address}, expected "
                f"the COW token {cow_token_address}: {transfer}"
            )
        else:
            report.warning(
                f"Unmatched transfer, not verified against Dune data: {transfer}"
            )

    return report


def compare_safe_exports(  # pylint: disable=too-many-arguments,too-many-locals,too-many-branches
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
) -> ComparisonReport:
    """Set-based comparison using separate COW and native transfer lists.

    Unlike ``compare()``, transfers may appear in any order.  Each expected
    solver transfer is located by (receiver, amount) in the respective list.

    Protocol fee verification (optional):
        If both ``protocol_fee`` and ``protocol_fee_safe`` are provided, the
        function looks for a native transfer to ``protocol_fee_safe`` with
        amount ≈ ``protocol_fee`` (from the Dune Fees
        export) and verifies it.  A missing match is an error.

    Unmatched transfers:
        After solver and protocol-fee matching, remaining transfers land in
        ``report.unmatched_transfers``.  Transfers to the ``protocol_fee_safe``
        address are labelled as "partner fee tax"; all others as generic
        unmatched (partner fee transfers).  Every unmatched transfer produces a
        warning.  Any Dune entry whose expected transfer is absent is an error.
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

    # Protocol fee verification (optional).
    protocol_fee_safe_lower = protocol_fee_safe.lower() if protocol_fee_safe else None
    if protocol_fee is not None and protocol_fee_safe_lower:
        t = find_and_remove(remaining_native, protocol_fee_safe_lower, protocol_fee)
        if t is None:
            report.error(
                f"Missing protocol fee transfer of {protocol_fee} native to "
                f"{protocol_fee_safe_lower}"
            )

    # Any transfers not matched to a Dune entry or protocol fee.
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
        elif protocol_fee_safe_lower and transfer.receiver == protocol_fee_safe_lower:
            report.warning(
                f"Unverified fee transfer to protocol safe "
                f"(likely partner fee tax): {transfer}"
            )
        else:
            report.warning(
                f"Unmatched transfer, not verified against Dune data: {transfer}"
            )

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
    print()

    if report.is_valid:
        print("✅ Transaction is valid: ok to sign")
    else:
        print("\U0001f6ab Transaction is NOT valid: do not sign")


def parse_args(argv: Optional[list[str]] = None) -> argparse.Namespace:
    """Parse CLI arguments."""
    parser = argparse.ArgumentParser(
        description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter
    )
    parser.add_argument("dune_csv", help="Path to the Dune solver-rewards CSV export")

    mode = parser.add_mutually_exclusive_group(required=True)
    mode.add_argument(
        "transfers_csv",
        nargs="?",
        help=(
            "Path to a combined transfers CSV (token_type/token_address/receiver/amount). "
            "Mutually exclusive with --cow-safe-csv / --native-safe-csv."
        ),
    )
    mode.add_argument(
        "--cow-safe-csv",
        metavar="PATH",
        help="Safe transaction-export CSV for COW transfers (mainnet Safe).",
    )

    parser.add_argument(
        "--native-safe-csv",
        metavar="PATH",
        help=(
            "Safe transaction-export CSV for native transfers (network Safe). "
            "Required when --cow-safe-csv is used."
        ),
    )
    parser.add_argument(
        "-n",
        "--network",
        choices=sorted(COW_TOKEN_ADDRESSES),
        required=True,
        help="Network the rewards are for, used to look up the expected COW token address",
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
        help="Minimum native reward that must be reflected as a transfer (default: %(default)s)",
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
            "Dune Fees CSV export. When provided, the "
            "protocol_fee_in_native_token value is matched against a transfer "
            "to --protocol-fee-safe and verified."
        ),
    )
    parser.add_argument(
        "--protocol-fee-safe",
        metavar="ADDR",
        help=(
            "Address of the protocol fee safe (DAO wallet). Required when "
            "--fees-csv is used. Transfers to this address are classified as "
            "protocol fee or partner fee tax."
        ),
    )
    return parser.parse_args(argv)


def main(argv: Optional[list[str]] = None) -> int:
    """Entry point: parse args, run comparison, print report."""
    args = parse_args(argv)

    dune_rewards = load_dune_rewards(args.dune_csv)
    cow_token_address = COW_TOKEN_ADDRESSES[args.network]
    kwargs = {
        "cow_token_address": cow_token_address,
        "cow_threshold": args.cow_threshold,
        "native_threshold": args.native_threshold,
        "tolerance": args.tolerance,
    }

    if args.cow_safe_csv:
        if not args.native_safe_csv:
            print(
                "error: --native-safe-csv is required when --cow-safe-csv is used",
                file=sys.stderr,
            )
            return 2

        fee_kwargs: dict = {}
        if args.fees_csv:
            if not args.protocol_fee_safe:
                print(
                    "error: --protocol-fee-safe is required when --fees-csv is used",
                    file=sys.stderr,
                )
                return 2
            fee_summary = load_fee_summary(args.fees_csv)
            fee_kwargs = {
                "protocol_fee": fee_summary.protocol_fee,
                "protocol_fee_safe": args.protocol_fee_safe,
            }

        cow_transfers = load_safe_transfers(args.cow_safe_csv, cow_token_address)
        native_transfers = load_safe_transfers(args.native_safe_csv, cow_token_address)
        report = compare_safe_exports(
            dune_rewards, cow_transfers, native_transfers, **kwargs, **fee_kwargs
        )
    else:
        transfers = load_transfers(args.transfers_csv)
        report = compare(dune_rewards, transfers, **kwargs)

    print_report(report)

    return 0 if report.is_valid else 1


if __name__ == "__main__":
    sys.exit(main())
