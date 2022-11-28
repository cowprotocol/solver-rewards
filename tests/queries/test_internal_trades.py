from __future__ import annotations

import os
import unittest
from dataclasses import dataclass
from enum import Enum
from typing import Optional

from dune_client.client import DuneClient
from dune_client.types import Address, QueryParameter

from src.models.accounting_period import AccountingPeriod
from src.queries import QUERIES, DuneVersion
from tests.integration.common import exec_or_get


class TransferType(Enum):
    """
    Classifications of Internal Token Transfers
    """

    IN_AMM = "IN_AMM"
    OUT_AMM = "OUT_AMM"
    IN_USER = "IN_USER"
    OUT_USER = "OUT_USER"
    INTERNAL_TRADE = "INTERNAL_TRADE"

    @classmethod
    def from_str(cls, type_str: str) -> TransferType:
        """Constructs Enum variant from string (case-insensitive)"""
        try:
            return cls[type_str.upper()]
        except KeyError as err:
            raise ValueError(f"No TransferType {type_str}!") from err


@dataclass
class InternalTransfer:
    """Total amount reimbursed for accounting period"""

    transfer_type: TransferType
    token: Address
    amount: float

    @classmethod
    def from_dict(cls, obj: dict[str, str]) -> InternalTransfer:
        """Converts Dune data dict to object with types"""
        return cls(
            transfer_type=TransferType.from_str(obj["transfer_type"]),
            token=Address(obj["token"]),
            amount=float(obj["amount"]),
        )

    @staticmethod
    def filter_by_type(
        recs: list[InternalTransfer], transfer_type: TransferType
    ) -> list[InternalTransfer]:
        """Filters list of records returning only those with indicated TransferType"""
        return list(filter(lambda r: r.transfer_type == transfer_type, recs))

    @classmethod
    def internal_trades(cls, recs: list[InternalTransfer]) -> list[InternalTransfer]:
        """Filters records returning only Internal Trade types."""
        return cls.filter_by_type(recs, TransferType.INTERNAL_TRADE)


def token_slippage(
    token_str: str,
    internal_trade_list: list[InternalTransfer],
) -> float:
    return sum(a.amount for a in internal_trade_list if a.token == Address(token_str))


class TestInternalTrades(unittest.TestCase):
    def setUp(self) -> None:
        # We used to use this local postgres instance.
        # self.dune = DBRouter(ConnectionType.LOCAL)
        self.dune = DuneClient(os.environ["DUNE_API_KEY"])

        self.period = AccountingPeriod("2022-03-01", length_days=10)
        self.slippage_query = QUERIES["PERIOD_SLIPPAGE"]

    # def tearDown(self) -> None:
    #     self.dune.close()

    def get_internal_transfers(
        self, tx_hash: str, result_id: Optional[str] = None
    ) -> list[InternalTransfer]:
        query = self.slippage_query.with_params(
            self.period.as_query_params()
            + [
                # Default values (on the query definition) do not need to be provided!
                QueryParameter.text_type("TxHash", tx_hash),
                # QueryParameter.text_type("Solver", "0x")
                QueryParameter.text_type(
                    "CTE_NAME", "incoming_and_outgoing_with_buffer_trades"
                ),
            ],
            dune_version=DuneVersion.V2,
        )
        data_set = exec_or_get(self.dune, query, result_id).get_rows()
        return [InternalTransfer.from_dict(row) for row in data_set]

    def internal_trades_for_tx(
        self, tx_hash: str, result_id: Optional[str] = None
    ) -> list[InternalTransfer]:
        internal_transfers = self.get_internal_transfers(tx_hash, result_id)
        return InternalTransfer.internal_trades(internal_transfers)

    def test_one_buffer_trade(self):
        """
        tx: 0xd6b85ada980d10a11a5b6989c72e0232015ce16e7331524b38180b85f1aea6c8
        This transaction has 1 buffer trade wNXM for Ether
        """
        internal_transfers = self.get_internal_transfers(
            "0xd6b85ada980d10a11a5b6989c72e0232015ce16e7331524b38180b85f1aea6c8",
            result_id="01GJXD0NK4AWS2ZVGWFDR5SXHX",
        )
        internal_trades = InternalTransfer.internal_trades(internal_transfers)
        self.assertEqual(1 * 2, len(internal_trades))
        # We had 0.91 USDT positive slippage
        self.assertEqual(
            916698,
            token_slippage(
                "0xA0b86991c6218b36c1d19D4a2e9Eb0cE3606eB48", internal_transfers
            ),
        )

    def test_one_buffer_trade_with_big_deviation_from_clearing_prices(self):
        """
        tx: 0x9a318d1abd997bcf8afed55b2946a7b1bd919d227f094cdcc99d8d6155808d7c
        This transaction has 1 buffer trade: 12.3 Strong for LIDO. The matchabilty check
        - abs((a.clearing_value + b.clearing_value) /(abs(a.clearing_value) + abs(b.clearing_value))) -
        evaluates to a high number of 0.021
        The positive slippage captured in WETH also scores a good matchablity to LIDO with a score of 0.026,
        but it should not be recognized by our algorithm
        """
        internal_trades = self.internal_trades_for_tx(
            "0x9a318d1abd997bcf8afed55b2946a7b1bd919d227f094cdcc99d8d6155808d7c",
            result_id="01GJXDCT8JY04FAZZC31K1ZKJM",
        )
        self.assertEqual(len(internal_trades), 1 * 2)

    def test_does_not_recognize_selling_too_much_and_buying_too_much_as_internal_trade(
        self,
    ):
        """
        tx: 0x63e234a1a0d657f5725817f8d829c4e14d8194fdc49b5bc09322179ff99619e7
        In this transaction, the solver sells too much USDC and buys too much ETH.
        These trades could be seen as buffer trades, but they should not:
        These kinds of trades can drain the buffers over time, as the prices of trading
        includes the AMM fees and hence are unfavourable for the buffers. Also, they are avoidable
        by using buyOrder on the AMMs.
        """
        internal_trades = self.internal_trades_for_tx(
            "0x63e234a1a0d657f5725817f8d829c4e14d8194fdc49b5bc09322179ff99619e7",
            result_id="01GJXDG7WT3B6S3RTJFT13166Y",
        )
        self.assertEqual(len(internal_trades), 0 * 2)

    def test_does_filter_out_SOR_internal_trades_with_amm_interactions(self):
        """
        tx: 0x0ae4775b0a352f7ba61f5ec301aa6ac4de19b43f90d8a8674b6e5c8116eda96b
        In this transaction, the solver sells too much XFT and buys too much DAI. Usually
        this would be seen as an internal buffer trade, as the amounts match perfectly and DAI
        is in the allowed buffer token list. However, since the solution is coming from 0x,
        it cannot be and internal buffer trade, given that the settlement had also an AMM interaction.
        """
        internal_transfers = self.get_internal_transfers(
            "0x0ae4775b0a352f7ba61f5ec301aa6ac4de19b43f90d8a8674b6e5c8116eda96b",
            result_id="01GJXDQE1X33N6Y9HTR1G2J16Y",
        )
        internal_trades = InternalTransfer.internal_trades(internal_transfers)
        self.assertEqual(len(internal_trades), 0 * 2)
        self.assertAlmostEqual(
            token_slippage(
                "0x6B175474E89094C44Da98b954EedeAC495271d0F", internal_transfers
            )
            / 10**18,
            4494166090057377749 / 10**18,
            places=12,
        )

    def test_does_recognize_slippage_due_to_buffer_token_list(self):
        """
        tx: 0x0bd527494e8efbf4c3013d1e355976ed90fa4e3b79d1f2c2a2690b02baae4abe
        This tx has an internal trade between pickle and eth. As pickle is not in the allow-list,
        the internal trade was not allowed.
        Our queries should recognize these kinds of trades as slippage and not as a internal trades.
        """
        internal_transfers = self.get_internal_transfers(
            "0x0bd527494e8efbf4c3013d1e355976ed90fa4e3b79d1f2c2a2690b02baae4abe",
            result_id="01GJXDJ57JTGCCPN6FDKK4Y41N",
        )
        internal_trades = InternalTransfer.internal_trades(internal_transfers)
        self.assertEqual(len(internal_trades), 0 * 2)
        self.assertEqual(
            token_slippage(
                "0xC02aaA39b223FE8D0A0e5C4F27eAD9083C756Cc2", internal_transfers
            )
            / 10**18,
            -678305196269132000 / 10**18,
        )

    def test_zero_buffer_trade(self):
        """
        tx: 0x31ab7acdadc65944a3f9507793ba9c3c58a1add35de338aa840ac951a24dc5bc
        Although there are two quite similar trades TOKE for ETH,
        the script should **not** detect a buffer trade
        """
        internal_trades = self.internal_trades_for_tx(
            "0x31ab7acdadc65944a3f9507793ba9c3c58a1add35de338aa840ac951a24dc5bc",
            result_id="01GJXDXWYSBW982X26WTV6HZHE",
        )
        self.assertEqual(len(internal_trades), 0 * 2)

    def test_buffer_trade_with_missing_price_from_pricesUSD(self):
        """
        tx: 0x80ae1c6a5224da60a1bf188f2101bd154e29ef71d54d136bfd1f6cc529f9d7ef
        CRVCX is not part of the priceUSD list from dune, still we are finding the internal trade
        """
        internal_transfers = self.get_internal_transfers(
            tx_hash="0x80ae1c6a5224da60a1bf188f2101bd154e29ef71d54d136bfd1f6cc529f9d7ef",
            result_id="01GJXE1WHP39XXHGPKX4NMW12N",
        )
        internal_trades = InternalTransfer.internal_trades(internal_transfers)

        self.assertEqual(1 * 2, len(internal_trades))
        self.assertEqual(
            token_slippage(
                "0xD533a949740bb3306d119CC777fa900bA034cd52", internal_transfers
            ),
            0,
        )
        self.assertEqual(
            token_slippage(
                "0x62B9c7356A2Dc64a1969e19C23e4f579F9810Aa7", internal_transfers
            ),
            0,
        )

    def test_buffer_trade_with_missing_price_from_pricesUSD_2(self):
        """
        tx: 0x1b4a299bfd2bb97e2289260495f566b750b9b62856b061f31d5186ae3b5ddce7
        This tx has an illegal internal buffer trade, it was not allowed to sell UBI
        to the contract
        """
        internal_transfers = self.get_internal_transfers(
            tx_hash="0x1b4a299bfd2bb97e2289260495f566b750b9b62856b061f31d5186ae3b5ddce7",
            result_id="01GJXE3S8VS6GBB21YZST2Z9HY",
        )
        internal_trades = InternalTransfer.internal_trades(internal_transfers)

        self.assertEqual(len(internal_trades), 0 * 2)
        self.assertAlmostEqual(
            int(
                token_slippage(
                    "0xDd1Ad9A21Ce722C151A836373baBe42c868cE9a4", internal_transfers
                )
            ),
            3262425415624260124672,
            delta=10**6,
        )
        self.assertEqual(
            token_slippage(
                "0xC02aaA39b223FE8D0A0e5C4F27eAD9083C756Cc2", internal_transfers
            ),
            -61150200744955688,
        )

    def test_buffer_trade_without_gp_settlement_price(self):
        """
        tx: 0x20ae31d11dba93d372ecf9d0cb387ea446e88572ce2d3d8e3d410871cfe6ec49
        This settlement has an internal tx between WETH and FOLD,
        but there are no settlement prices for WETH in the call data
        """
        internal_trades = self.internal_trades_for_tx(
            "0x20ae31d11dba93d372ecf9d0cb387ea446e88572ce2d3d8e3d410871cfe6ec49",
            result_id="01GJXEA4VFPSAJHQGNXYN3BKKF",
        )
        self.assertEqual(len(internal_trades), 1 * 2)

    def test_it_recognizes_slippage(self):
        """
        tx: 0x703474ed43faadc35364254e4f9448e275c7cfe9cf60beddbdd68a462bf7f433
        Paraswap returns to little UST, but our buffers make up for it
        """
        internal_transfers = self.get_internal_transfers(
            tx_hash="0x703474ed43faadc35364254e4f9448e275c7cfe9cf60beddbdd68a462bf7f433",
            result_id="01GJXECYGGT3TMA95F91SB9VM3",
        )
        # We lost 58 UST dollars:
        self.assertAlmostEqual(
            token_slippage(
                "0xa47c8bf37f92aBed4A126BDA807A7b7498661acD", internal_transfers
            ),
            -57980197374074949357,
            delta=10**9,
        )
        internal_trades = InternalTransfer.internal_trades(internal_transfers)
        self.assertEqual(len(internal_trades), 0 * 2)

    def test_it_does_not_yet_find_the_internal_trades(self):
        """
        tx: 0x07e91a80955eac0ea2292efe13fa694aea9ba5ae575ced8532e61d5e4806e8b4
        This has two internal trades. Currently, we don't find any of them.
        TODO - Evaluating better solutions. If we would take out the sum grouping in
         potential_buffer_trades table, then we would find the correct solution here.
         But then we no longer find a good solution for testcase
         0x31ab7acdadc65944a3f9507793ba9c3c58a1add35de338aa840ac951a24dc5bc
        """
        internal_trades = self.internal_trades_for_tx(
            tx_hash="0x07e91a80955eac0ea2292efe13fa694aea9ba5ae575ced8532e61d5e4806e8b4",
            result_id="01GJXEKT30Y3Z569EEP2W9D50X",
        )
        self.assertEqual(len(internal_trades), 0 * 2)

    def test_does_not_find_slippage_for_internal_only_trades(self):
        """
        tx: 0x007a8534959a027c81f20c32dc3572f47cb7f19043d4a8d1e44379f363cb4c0f
        This settlement is so complicated that the query does not find the internal trades
        But since it has 0 dex interactions, we know that there can not be any slippage
        """
        internal_transfers = self.get_internal_transfers(
            tx_hash="0x007a8534959a027c81f20c32dc3572f47cb7f19043d4a8d1e44379f363cb4c0f",
            result_id="01GJXEN4R97NDV72QQ8C986HK7",
        )
        self.assertEqual(
            token_slippage(
                "0xdAC17F958D2ee523a2206206994597C13D831ec7", internal_transfers
            ),
            0,
        )
        self.assertEqual(
            token_slippage(
                "0x990f341946A3fdB507aE7e52d17851B87168017c", internal_transfers
            ),
            0,
        )

    def test_excludes_batches_involving_axs_old(self):
        """
        tx: 0x5d74fde18840e02a0ca49cd3caff37b4c9b4b20c254692a629d75d93b5d69f89
        We do not expect to get any internal accounting data returned for this batch
        """
        self.assertEqual(
            self.get_internal_transfers(
                tx_hash="0x5d74fde18840e02a0ca49cd3caff37b4c9b4b20c254692a629d75d93b5d69f89",
                result_id="01GJXEP6DPVD7BGY3HKW23PPHB",
            ),
            [],
        )


if __name__ == "__main__":
    unittest.main()
