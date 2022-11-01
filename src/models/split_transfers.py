"""
The Split Transfer Class is responsible for processing a mixed list of transfers.
It exposes only one public method "process" which ensures that its
internal methods are called in the appropriate order.
"""
from __future__ import annotations

from datetime import timedelta
from typing import Optional

from duneapi.types import Address

from src.fetch.reward_targets import Vouch
from src.models.accounting_period import AccountingPeriod
from src.models.overdraft import Overdraft
from src.models.slippage import SolverSlippage
from src.models.token import TokenType
from src.models.transfer import Transfer
from src.utils.prices import eth_in_token, TokenId, token_in_eth
from src.utils.print_store import Category, PrintStore


# pylint: disable=too-few-public-methods
class SplitTransfers:
    """
    This class keeps the ERC20 and NATIVE token transfers Split.
    Technically we should have two additional classes one for each token type.
    """

    def __init__(self, period: AccountingPeriod, mixed_transfers: list[Transfer]):
        self.period = period
        self.unprocessed_native = []
        self.unprocessed_cow = []
        for transfer in mixed_transfers:
            if transfer.token_type == TokenType.NATIVE:
                self.unprocessed_native.append(transfer)
            elif transfer.token_type == TokenType.ERC20:
                self.unprocessed_cow.append(transfer)
            else:
                raise ValueError(f"Invalid token type! {transfer.token_type}")
        # Initialize empty overdraft
        self.overdrafts: dict[Address, Overdraft] = {}
        self.eth_transfers: list[Transfer] = []
        self.cow_transfers: list[Transfer] = []

    def _process_native_transfers(
        self, indexed_slippage: dict[Address, SolverSlippage], log_saver: PrintStore
    ) -> int:
        penalty_total = 0
        while self.unprocessed_native:
            transfer = self.unprocessed_native.pop(0)
            solver = transfer.receiver
            slippage: Optional[SolverSlippage] = indexed_slippage.get(solver)
            if slippage is not None:
                try:
                    transfer.add_slippage(slippage, log_saver)
                    penalty_total += slippage.amount_wei
                except ValueError as err:
                    name, address = slippage.solver_name, slippage.solver_address
                    log_saver.print(
                        f"Slippage for {address}({name}) exceeds reimbursement: {err}\n"
                        f"Excluding payout and appending excess to overdraft",
                        category=Category.OVERDRAFT,
                    )
                    self.overdrafts[solver] = Overdraft.from_objects(
                        transfer, slippage, self.period
                    )
                    # Deduct entire transfer value.
                    penalty_total -= transfer.amount_wei
                    continue
            self.eth_transfers.append(transfer)
        return penalty_total

    def _process_token_transfers(
        self, cow_redirects: dict[Address, Vouch], log_saver: PrintStore
    ) -> None:
        price_day = self.period.end - timedelta(days=1)
        while self.unprocessed_cow:
            transfer = self.unprocessed_cow.pop(0)
            solver = transfer.receiver
            # Remove the element if it exists (assuming it won't have to be reinserted)
            overdraft = self.overdrafts.pop(solver, None)
            if overdraft is not None:
                cow_deduction = eth_in_token(TokenId.COW, overdraft.wei, price_day)
                log_saver.print(
                    f"Deducting {cow_deduction} COW from reward for {solver}",
                    category=Category.OVERDRAFT,
                )
                transfer.amount_wei -= cow_deduction
                if transfer.amount_wei < 0:
                    log_saver.print(
                        "Overdraft exceeds COW reward! "
                        "Excluding reward and updating overdraft",
                        category=Category.OVERDRAFT,
                    )
                    overdraft.wei = token_in_eth(
                        TokenId.COW, abs(transfer.amount_wei), price_day
                    )
                    # Reinsert since there is still an amount owed.
                    self.overdrafts[solver] = overdraft
                    continue
            if solver in cow_redirects:
                # Redirect COW rewards to reward target specific by VouchRegistry
                redirect_address = cow_redirects[solver].reward_target
                log_saver.print(
                    f"Redirecting solver {solver} COW tokens "
                    f"({transfer.amount}) to {redirect_address}",
                    category=Category.REDIRECT,
                )
                transfer.receiver = redirect_address
            self.cow_transfers.append(transfer)

    def process(
        self,
        indexed_slippage: dict[Address, SolverSlippage],
        cow_redirects: dict[Address, Vouch],
        log_saver: PrintStore,
    ) -> list[Transfer]:
        """
        This is the public interface to construct the final transfer file based on
        raw (unpenalized) results, slippage penalty, redirected rewards and overdrafts.
        It is very important that the native token transfers are processed first,
        so that and overdraft from slippage can be carried over and deducted from
        the COW rewards.
        """
        penalty_total = self._process_native_transfers(indexed_slippage, log_saver)
        self._process_token_transfers(cow_redirects, log_saver)
        log_saver.print(
            f"Total Slippage deducted (ETH): {penalty_total / 10**18}",
            category=Category.TOTALS,
        )
        if self.overdrafts:
            accounts_owing = "\n".join(map(str, self.overdrafts.values()))
            log_saver.print(
                f"Additional owed\n {accounts_owing}", category=Category.OVERDRAFT
            )
        return self.cow_transfers + self.eth_transfers


# pylint: enable=too-few-public-methods
