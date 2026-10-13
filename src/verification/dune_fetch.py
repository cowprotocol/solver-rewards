"""Fetches the Dune data consumed by compare_output_files.py directly from the Dune API.

Given an accounting period start date and a target network, this replaces the need to
manually download the solver-rewards and partner-fees CSVs from the Dune UI before
running the verification script.

Relevant Dune queries, all parameterised by the same (blockchain, start_time,
end_time) accounting period:
    - Solver rewards (public): dune.com/queries/2510345, the "Period Solver Rewards"
      table of the cow-solver-rewards dashboard.
    - Protocol fees (public): dune.com/queries/2601653, the "V3: Weekly Cost Coverage
      (Fees - Reimbursement)" table of the same dashboard. Its
      protocol_fee_in_native_token column is the protocol fee net of partner fees -
      i.e. the "Protocol Fees (excluding partner fees)" line of the payment breakdown
      the payouts script posts to Slack, and the amount transferred to the protocol
      fee safe.
    - Partner fees (private): dune.com/queries/3602560

Note: compare_output_files.py only imports this module lazily, inside main(), so this
never actually cycles at runtime; the module-level import back into it below is still
flagged statically.
"""

# pylint: disable=cyclic-import

from __future__ import annotations

import os

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
COST_COVERAGE_QUERY_ID = (
    2601653  # cow-solver-rewards dashboard, "V3: Weekly Cost Coverage"
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


def fetch_solver_rewards(
    dune: DuneClient, network: Network, period: AccountingPeriod
) -> list[DuneReward]:
    """Fetches the per-solver rewards/transfers table for the accounting period."""
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
    return [DuneReward.from_csv_row(row) for row in rows]


def fetch_fee_summary(
    dune: DuneClient, network: Network, period: AccountingPeriod
) -> FeeSummary:
    """Fetches the net protocol fee for the accounting period.

    This is the ``protocol_fee_in_native_token`` column of the weekly cost-coverage
    table, which already nets out partner fees, and so is exactly the amount expected
    to be transferred to the protocol fee safe. The partner-fee *tax* going to the
    same safe is a separate transfer, verified from the partner-fees data.
    """
    params = _period_and_network_params(network, period)
    rows = _fetch_rows(
        dune, QueryBase(COST_COVERAGE_QUERY_ID, "V3: Weekly Cost Coverage", params)
    )
    if not rows:
        raise ValueError(
            f"Dune query {COST_COVERAGE_QUERY_ID} returned no rows for {period} on "
            f"{network.value}; pass --fees-csv to supply the protocol fee manually."
        )
    raw_value = rows[0].get("protocol_fee_in_native_token")
    if raw_value is None or raw_value == "":
        raise ValueError(
            f"Dune query {COST_COVERAGE_QUERY_ID} returned no "
            "'protocol_fee_in_native_token' value; pass --fees-csv to supply the "
            "protocol fee manually."
        )
    return FeeSummary(protocol_fee=parse_amount(raw_value))


def fetch_partner_fees(
    dune: DuneClient, network: Network, period: AccountingPeriod
) -> list[PartnerFee]:
    """Fetches partner fees from the private Dune query."""
    params = _period_and_network_params(network, period)
    rows = _fetch_rows(dune, QueryBase(PARTNER_FEES_QUERY_ID, "Partner Fees", params))
    return [PartnerFee.from_csv_row(row) for row in rows]
