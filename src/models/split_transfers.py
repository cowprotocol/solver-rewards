"""
The Split Transfer Class is responsible for processing a mixed list of transfers.
It exposes only one public method "process" which ensures that its
internal methods are called in the appropriate order.
"""
from __future__ import annotations

from datetime import timedelta
from typing import Optional

from dune_client.types import Address

from src.models.vouch import Vouch
from src.models.accounting_period import AccountingPeriod
from src.models.overdraft import Overdraft
from src.models.slippage import SolverSlippage, SplitSlippages
from src.models.token import TokenType
from src.models.transfer import Transfer
from src.fetch.prices import eth_in_token, TokenId, token_in_eth
from src.utils.dataset import index_by
from src.utils.print_store import Category, PrintStore


# pylint: disable=too-few-public-methods
class SplitTransfers:
    """
    This class keeps the ERC20 and NATIVE token transfers Split.
    Technically we should have two additional classes one for each token type.
    """

    def __init__(
        self,
        period: AccountingPeriod,
        mixed_transfers: list[Transfer],
        log_saver: PrintStore,
    ):
        self.log_saver = log_saver
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
        self, indexed_slippage: dict[Address, SolverSlippage]
    ) -> int:
        """
        Draining the `unprocessed_native` (ETH) transfers into processed
        versions as `eth_transfers`. Processing adjusts for negative slippage by deduction.
        Returns: total negative slippage
        """
        penalty_total = 0
        while self.unprocessed_native:
            transfer = self.unprocessed_native.pop(0)
            solver = transfer.receiver
            slippage: Optional[SolverSlippage] = indexed_slippage.get(solver)
            if slippage is not None:
                assert (
                    slippage.amount_wei < 0
                ), f"Expected negative slippage! Got {slippage}"
                try:
                    transfer.add_slippage(slippage, self.log_saver)
                    penalty_total += slippage.amount_wei
                except ValueError as err:
                    name, address = slippage.solver_name, slippage.solver_address
                    self.log_saver.print(
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

    def _process_rewards(
        self,
        redirect_map: dict[Address, Vouch],
        positive_slippage: list[SolverSlippage],
    ) -> int:
        """
        Draining the `unprocessed_cow` (COW) transfers into processed versions
        as `cow_transfers`. Processing accounts for overdraft and positive slippage.
        Returns: total positive slippage
        """
        price_day = self.period.end - timedelta(days=1)
        while self.unprocessed_cow:
            transfer = self.unprocessed_cow.pop(0)
            solver = transfer.receiver
            # Remove the element if it exists (assuming it won't have to be reinserted)
            overdraft = self.overdrafts.pop(solver, None)
            if overdraft is not None:
                cow_deduction = eth_in_token(TokenId.COW, overdraft.wei, price_day)
                self.log_saver.print(
                    f"Deducting {cow_deduction} COW from reward for {solver}",
                    category=Category.OVERDRAFT,
                )
                transfer.amount_wei -= cow_deduction
                if transfer.amount_wei < 0:
                    self.log_saver.print(
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
            transfer.redirect_to(redirect_map, self.log_saver)
            self.cow_transfers.append(transfer)
        # We do not need to worry about any controversy between overdraft
        # and positive slippage adjustments, because positive/negative slippage
        # is disjoint between solvers.
        total_positive_slippage = 0
        while positive_slippage:
            slippage = positive_slippage.pop()
            assert (
                slippage.amount_wei > 0
            ), f"Expected positive slippage got {slippage.amount_wei}"
            total_positive_slippage += slippage.amount_wei
            slippage_transfer = Transfer.from_slippage(slippage)
            slippage_transfer.redirect_to(redirect_map, self.log_saver)
            self.eth_transfers.append(slippage_transfer)
        return total_positive_slippage

    def process(
        self,
        slippages: SplitSlippages,
        cow_redirects: dict[Address, Vouch],
    ) -> list[Transfer]:
        """
        This is the public interface to construct the final transfer file based on
        raw (unpenalized) results, positive, negative slippage, rewards and overdrafts.
        It is very important that the native token transfers are processed first,
        so that any overdraft from slippage can be carried over and deducted from
        the COW rewards.
        """
        total_penalty = self._process_native_transfers(
            indexed_slippage=index_by(
                slippages.solvers_with_negative_total, "solver_address"
            )
        )
        self.log_saver.print(
            f"Total Negative Slippage (ETH): {total_penalty / 10**18:.4f}",
            category=Category.TOTALS,
        )
        # Note that positive and negative slippage is DISJOINT.
        # So no overdraft computations will overlap with the positive slippage perturbations.
        total_positive_slippage = self._process_rewards(
            cow_redirects,
            positive_slippage=slippages.solvers_with_positive_total,
        )
        self.log_saver.print(
            f"Total Positive Slippage (ETH): {total_positive_slippage / 10**18:.4f}",
            category=Category.TOTALS,
        )
        if self.overdrafts:
            accounts_owing = "\n".join(map(str, self.overdrafts.values()))
            self.log_saver.print(
                f"Additional owed\n {accounts_owing}", category=Category.OVERDRAFT
            )
        return self.cow_transfers + self.eth_transfers


# pylint: enable=too-few-public-methods
