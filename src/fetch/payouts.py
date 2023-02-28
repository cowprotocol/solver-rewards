"""Logic for Post CIP 20 Solver Payout Calculation"""
from dataclasses import dataclass
from datetime import timedelta

from dune_client.types import Address
from pandas import DataFrame

from src.constants import COW_TOKEN_ADDRESS
from src.fetch.dune import DuneFetcher
from src.fetch.prices import eth_in_token, TokenId, token_in_eth
from src.models.accounting_period import AccountingPeriod
from src.models.overdraft import Overdraft
from src.models.split_transfers import SplitTransfers
from src.models.token import Token
from src.models.transfer import Transfer
from src.pg_client import MultiInstanceDBFetcher

PERIOD_BUDGET_COW = 1


@dataclass
class Payments:
    """Dataclass to keep track of reimbursements and rewards"""

    negative_payments: list[Overdraft]
    # ETH Reimbursements
    reimbursements: list[Transfer]
    # COW Rewards
    rewards: list[Transfer]


def split_into_eth_cow(pdf: DataFrame, period: AccountingPeriod) -> Payments:
    """
    Manipulates the payout DataFrame to split into ETH and COW.
    Specifically, We deduct total_rewards by total_execution_cost (both initially in ETH)
    keep the execution cost in ETH and convert the difference to COW.
    """
    price_day = period.end - timedelta(days=1)
    # Note that this can be negative!
    pdf["reward_eth"] = pdf["payment_eth"] - pdf["execution_cost_eth"]
    pdf["reward_cow"] = pdf["reward_eth"].apply(
        lambda t: eth_in_token(TokenId.COW, t, day=price_day)
    )

    secondary_allocation = max(PERIOD_BUDGET_COW - pdf["reward_cow"].sum(), 0)
    participation_total = pdf["num_participating_batches"].sum()
    pdf["secondary_reward_cow"] = (
        secondary_allocation * pdf["num_participating_batches"] / participation_total
    )
    pdf["secondary_reward_eth"] = pdf["secondary_reward_cow"].apply(
        lambda t: token_in_eth(TokenId.COW, t, day=price_day)
    )

    negative_payments, reimbursements, rewards = [], [], []
    for _, payment in pdf.iterrows():
        solver = payment["solver"]
        primary_eth = payment["payment_eth"]
        exec_cost = payment["execution_cost_eth"]
        secondary_eth = payment["secondary_reward_eth"]
        total_eth = primary_eth + secondary_eth

        if total_eth < 0:
            # Solver owes us! ETH or COW.
            print(f"Solver {payment['solver']} owes us! ETH or COW.")
            negative_payments.append(
                Overdraft(
                    period=period,
                    account=Address(solver),
                    wei=-int(total_eth),
                )
            )
        elif total_eth < exec_cost:
            reimbursements.append(
                Transfer(
                    token=None, recipient=Address(solver), amount_wei=int(total_eth)
                )
            )
        else:
            reimbursements.append(
                Transfer(
                    token=None, recipient=Address(solver), amount_wei=int(exec_cost)
                )
            )
            rewards.append(
                Transfer(
                    token=Token(COW_TOKEN_ADDRESS),
                    recipient=Address(solver),
                    amount_wei=int(
                        payment["reward_cow"] + payment["secondary_reward_cow"]
                    ),
                )
            )

    return Payments(negative_payments, reimbursements, rewards)


def post_cip20_payouts(
    dune: DuneFetcher, orderbook: MultiInstanceDBFetcher
) -> list[Transfer]:
    """Workflow of solver reward payout logic post-CIP20"""
    # Fetch auction data from orderbook.
    rewards_df = orderbook.get_solver_rewards(dune.start_block, dune.end_block)

    # Separate values into ETH (execution costs) and COW rewards.
    payments = split_into_eth_cow(rewards_df, dune.period)

    # Everything below here is already existing and reviewed code:
    split_transfers = SplitTransfers(
        period=dune.period,
        mixed_transfers=payments.reimbursements + payments.rewards,
        log_saver=dune.log_saver,
    )
    return split_transfers.process(
        slippages=dune.get_period_slippage(),
        cow_redirects=dune.get_vouches(),
    )
