"""
Propose corrected native prices for protocol fees collected in tokens that have
no USD price on Dune.

For every chain, the script
  1. runs Dune query 8766284 ("Null Prices Protocol Fees"; https://dune.com/queries/8766284)
     for an accounting period (see `accounting_window`),
  2. for every fee worth more than --min-fee-usd, fetches the token's price
     from Moralis at the block of the trade,
  3. proposes Moralis' price when the native price is more than --tolerance above it
     (conservative: prices are only ever corrected downwards),
and writes

    network,environment,auction_id,token,price

where price is Moralis' price of one atom of the token, in atoms of the native
token, multiplied by 10^18 (i.e. one atom of the native token has price 10^18).

Usage:
    python -m src.price_corrections.null_price_fees [--chains bnb polygon] [--start 2026-10-06]

Requires DUNE_API_KEY and MORALIS_API_KEY (environment or .env).
"""

from __future__ import annotations

import argparse
import csv
import logging
import os
import sys
from dataclasses import dataclass
from datetime import datetime, timedelta, timezone
from pathlib import Path
from typing import Any

from dune_client.client import DuneClient
from dune_client.types import QueryParameter

from src.models.accounting_period import DATE_FORMAT, AccountingPeriod
from src.price_corrections_script.moralis_api import CHAINS, ChainConfig, MoralisClient
from src.queries import QueryData

log = logging.getLogger(__name__)

NULL_PRICE_FEES_QUERY = QueryData(name="Null Prices Protocol Fees", q_id=8766284)
NATIVE_PLACEHOLDERS = {
    "0xeeeeeeeeeeeeeeeeeeeeeeeeeeeeeeeeeeeeeeee",
    "0x0000000000000000000000000000000000000000",
}
PRICE_SCALE = 10**18
OUTPUT_HEADER = ["network", "environment", "auction_id", "token", "price"]


@dataclass
class Correction:
    """One proposed price correction (one output line)."""

    network: str
    environment: str
    auction_id: int
    token: str
    price: int

    def key(self) -> tuple[str, str, int, str]:
        """Identity of an output line."""
        return self.network, self.environment, self.auction_id, self.token

    def as_row(self) -> list[str]:
        """Values in OUTPUT_HEADER order."""
        return [
            self.network,
            self.environment,
            str(self.auction_id),
            self.token,
            str(self.price),
        ]


def fetch_null_price_fees_from_dune(
    dune: DuneClient, chain: ChainConfig, period: AccountingPeriod
) -> list[dict[str, Any]]:
    """Rows of query 8766284 for one chain and period."""
    query = NULL_PRICE_FEES_QUERY.with_params(
        period.as_query_params()
        + [QueryParameter.enum_type("blockchain", chain.dune_name)]
    )
    log.info(f"Running Dune query {query.query_id} for {chain.dune_name} ({period})")
    result = dune.refresh(query, ping_frequency=10)
    rows: list[dict[str, Any]] = result.get_rows()
    return rows


@dataclass(frozen=True)
class Thresholds:
    """When to check a fee and when to correct its price."""

    min_fee_usd: float
    tolerance: float


def check_row(
    row: dict[str, Any],
    chain: ChainConfig,
    moralis: MoralisClient,
    thresholds: Thresholds,
) -> tuple[str, Correction | None]:
    """Returns (status, correction). A correction is only returned when our
    implied price is more than `tolerance` above Moralis' price."""
    token = str(row["problematic_token_address"]).lower()
    if token in NATIVE_PLACEHOLDERS:
        return "NATIVE_TOKEN", None
    fee_atoms = int(row["protocol_fee"])
    fee_usd = float(row["protocol_fee_collected_usd"])
    if fee_atoms <= 0 or fee_usd <= thresholds.min_fee_usd:
        return "BELOW_THRESHOLD", None

    block_number = int(row["block_number"])
    moralis_response = moralis.price_at(chain, token, block_number)
    price = round(moralis_response.native_per_atom * PRICE_SCALE)

    # The fee value already uses the native price, so comparing USD
    # per atom is equivalent to comparing native prices.
    # To avoid division by zero, we first ensure that if the Moralis price is zero,
    # then we will always pick it.
    if moralis_response.usd_per_atom == 0:
        deviation = thresholds.tolerance
    else:
        deviation = (
            fee_usd / fee_atoms - moralis_response.usd_per_atom
        ) / moralis_response.usd_per_atom
    if deviation < thresholds.tolerance:
        # check if native price is within 50% either way away
        # from Moralis
        within = deviation >= -thresholds.tolerance
        return ("OK" if within else "KEPT_OURS_MORALIS_HIGHER"), None

    return "CORRECTED", Correction(
        network=chain.network.value,
        environment=str(row["environment"]),
        auction_id=int(row["auction_id"]),
        token=token,
        price=price,
    )


def run(
    chains: list[ChainConfig],
    period: AccountingPeriod,
    clients: tuple[DuneClient, MoralisClient],
    thresholds: Thresholds,
) -> list[Correction]:
    """Collect corrections for all chains, keeping one (the lowest) price per
    network/environment/auction/token."""
    dune, moralis = clients
    corrections: dict[tuple[str, str, int, str], Correction] = {}
    for chain in chains:
        for row in fetch_null_price_fees_from_dune(dune, chain, period):
            try:
                _, correction = check_row(row, chain, moralis, thresholds)
            except Exception as err:  # pylint: disable=broad-exception-caught
                correction = None
                log.warning(
                    f"{chain.dune_name} auction {row.get('auction_id')} "
                    f"token {row.get('problematic_token_address')}: {err}"
                )
            if correction is not None:
                existing = corrections.get(correction.key())
                if existing is None or correction.price < existing.price:
                    corrections[correction.key()] = correction
    return list(corrections.values())


def write_corrections(corrections: list[Correction], path: Path) -> None:
    """Write the output CSV."""
    path.parent.mkdir(parents=True, exist_ok=True)
    with open(path, "w", newline="", encoding="utf-8") as file:
        writer = csv.writer(file)
        writer.writerow(OUTPUT_HEADER)
        for correction in sorted(
            corrections, key=lambda c: (c.network, c.auction_id, c.token)
        ):
            writer.writerow(correction.as_row())


def main() -> None:
    """CLI entry point."""
    parser = argparse.ArgumentParser(
        description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter
    )
    parser.add_argument(
        "--chains",
        nargs="+",
        choices=list(CHAINS),
        default=list(CHAINS),
        help="Dune chain names to process (default: all)",
    )
    parser.add_argument(
        "--start",
        required=True,
        help=f"Period start ({DATE_FORMAT}). The period is always 7 days.",
    )
    parser.add_argument(
        "--min-fee-usd",
        type=float,
        default=5.0,
        help="only check fees worth more than this many USD (default 5)",
    )
    parser.add_argument(
        "--tolerance",
        type=float,
        default=0.5,
        help="correct only when our price exceeds Moralis' by more than this "
        "fraction (default 0.5, i.e. ours > 1.5x Moralis)",
    )
    parser.add_argument("-o", "--output", type=Path, help="output CSV path")
    args = parser.parse_args()

    logging.basicConfig(
        level=logging.INFO, format="%(asctime)s %(levelname)s %(message)s"
    )
    dune_key = os.environ.get("DUNE_API_KEY")
    moralis_key = os.environ.get("MORALIS_API_KEY")
    if not dune_key or not moralis_key:
        sys.exit("DUNE_API_KEY and MORALIS_API_KEY must be set (env or .env)")

    period = AccountingPeriod(args.start)
    output = args.output or Path("out") / f"null_price_corrections_{period}.csv"

    corrections = run(
        chains=[CHAINS[name] for name in args.chains],
        period=period,
        clients=(
            DuneClient(dune_key, request_timeout=60),
            MoralisClient(moralis_key),
        ),
        thresholds=Thresholds(args.min_fee_usd, args.tolerance),
    )
    write_corrections(corrections, output)
    log.info(f"Wrote {len(corrections)} correction(s) to {output}")


if __name__ == "__main__":
    main()
