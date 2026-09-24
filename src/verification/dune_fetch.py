"""Fetches the Dune data consumed by compare_output_files.py directly from the Dune API.

Given an accounting period start date and a target network, this replaces the need to
manually download the solver-rewards and partner-fees CSVs from the Dune UI before
running the verification script.

Relevant Dune queries:
    - Solver rewards (public): dune.com/cowprotocol/cow-solver-rewards
    - Partner fees (private): dune.com/queries/3602560

Note: the solver-rewards query does NOT include a protocol_fee_in_native_token column
(confirmed against a live fetch), so protocol-fee verification is not auto-fetchable
today - pass --fees-csv alongside --start if you also want that check.

Note: compare_output_files.py only imports this module lazily, inside main(), so this
never actually cycles at runtime; the module-level import back into it below is still
flagged statically.
"""

# pylint: disable=cyclic-import

from __future__ import annotations

import os
from typing import Optional

from dune_client.client import DuneClient
from dune_client.models import DuneError, ExecutionState
from dune_client.query import QueryBase
from dune_client.types import QueryParameter

from src.config import DuneConfig, Network, RewardConfig
from src.models.accounting_period import AccountingPeriod
from src.verification.compare_output_files import (
    DuneReward,
    FeeSummary,
    PartnerFee,
    parse_amount,
)

SOLVER_REWARDS_QUERY_ID = (
    2510345  # cow-solver-rewards dashboard, "Period Solver Rewards"
)
PARTNER_FEES_QUERY_ID = 3602560  # private


def make_dune_client() -> DuneClient:
    """Builds a DuneClient from the DUNE_API_KEY environment variable.

    Uses the "large" engine size: the solver-rewards query is heavy enough that the
    default "medium" cluster fails outright ("too many stages") when re-executed.
    """
    api_key = os.environ.get("DUNE_API_KEY", "")
    if not api_key:
        raise ValueError("DUNE_API_KEY environment variable is not set")
    return DuneClient(api_key, performance="large")


# How fresh a previously-computed result must be to reuse without re-executing the
# query. The solver-rewards query is heavy enough to fail outright ("too many stages")
# when re-executed on some Dune plans, so we strongly prefer the cached result that's
# already sitting behind the dashboard link this workflow tells people to check first.
_MAX_CACHE_AGE_HOURS = 24


_USABLE_STATES = (ExecutionState.COMPLETED, ExecutionState.PARTIAL)


def _fetch_rows(dune: DuneClient, query: QueryBase) -> list[dict]:
    try:
        result = dune.get_latest_result(query, max_age_hours=_MAX_CACHE_AGE_HOURS)
        needs_fresh_run = result.state not in _USABLE_STATES
    except DuneError:
        # No execution exists at all yet for these exact parameters.
        needs_fresh_run = True

    if needs_fresh_run:
        # Either there's no cached result for these parameters yet, or the cached
        # "latest" execution failed (e.g. a prior attempt on a too-small cluster) - a
        # missing/stale result shouldn't block us, so force a fresh execution rather
        # than immediately giving up.
        result = dune.refresh(query, ping_frequency=15)
    if result.state not in _USABLE_STATES:
        raise RuntimeError(
            f"Dune query {query.query_id}'s execution did not complete "
            f"(state={result.state.value}), even on the large engine size. Try opening "
            "the dashboard in a browser for these exact parameters, then re-run this. "
            "Alternatively, pass the data manually via --fees-csv/--partner-fees-csv/"
            "dune_csv."
        )
    return result.get_rows()


def _period_and_network_params(
    network: Network, period: AccountingPeriod
) -> list[QueryParameter]:
    blockchain = DuneConfig.from_network(network).dune_blockchain
    return period.as_query_params() + [
        QueryParameter.text_type("blockchain", blockchain),
    ]


def fetch_solver_rewards_and_fees(
    dune: DuneClient, network: Network, period: AccountingPeriod
) -> tuple[list[DuneReward], Optional[FeeSummary]]:
    """Fetches solver rewards, and the protocol fee summary if the query happens to
    include a protocol_fee_in_native_token column (it doesn't, as of this writing -
    pass --fees-csv for protocol-fee verification instead).
    """
    reward_config = RewardConfig.from_network(network)
    params = _period_and_network_params(network, period) + [
        QueryParameter.number_type(
            "quote_reward", reward_config.quote_reward_cow / 10**18
        ),
        QueryParameter.number_type(
            "quote_cap_native_token",
            reward_config.quote_reward_cap_native / 10**18,
        ),
    ]
    rows = _fetch_rows(
        dune, QueryBase(SOLVER_REWARDS_QUERY_ID, "Period Solver Rewards", params)
    )
    rewards = [DuneReward.from_csv_row(row) for row in rows]

    protocol_fee: float | None = None
    for row in rows:
        raw_value = row.get("protocol_fee_in_native_token")
        if raw_value is None or raw_value == "":
            continue
        fee = parse_amount(raw_value)
        if protocol_fee is not None and abs(fee - protocol_fee) > 1e-9:
            raise ValueError(
                "Conflicting 'protocol_fee_in_native_token' values in the solver "
                "rewards query result"
            )
        protocol_fee = fee
    fee_summary = (
        FeeSummary(protocol_fee=protocol_fee) if protocol_fee is not None else None
    )
    return rewards, fee_summary


def fetch_partner_fees(
    dune: DuneClient, network: Network, period: AccountingPeriod
) -> list[PartnerFee]:
    """Fetches partner fees from the private Dune query."""
    params = _period_and_network_params(network, period)
    rows = _fetch_rows(dune, QueryBase(PARTNER_FEES_QUERY_ID, "Partner Fees", params))
    return [PartnerFee.from_csv_row(row) for row in rows]
