import unittest
from datetime import datetime

from src.dune_analytics import DuneAnalytics, QueryParameter
from src.fetch.period_slippage import add_token_list_table_to_query
from src.file_io import File
from src.models import Address, InternalTokenTransfer, Network


def token_slippage(
    token_str: str,
    internal_trade_list: list[InternalTokenTransfer],
) -> int:
    return sum(a.amount for a in internal_trade_list if a.token == Address(token_str))


def get_internal_transfers(
    dune: DuneAnalytics, tx_hash: str, period_start: datetime, period_end: datetime
) -> list[InternalTokenTransfer]:
    path = "./queries/slippage"
    select_transfers_query = dune.open_query(
        File("select_in_out_with_buffers.sql", path).filename()
    )
    slippage_sub_query = dune.open_query(
        File("subquery_batchwise_internal_transfers.sql", path).filename()
    )
    query = "\n".join(
        [add_token_list_table_to_query(slippage_sub_query), select_transfers_query]
    )
    data_set = dune.fetch(
        query_str=query,
        network=Network.MAINNET,
        name="Internal Token Transfer Accounting",
        parameters=[
            QueryParameter.text_type("TxHash", tx_hash),
            QueryParameter.date_type("StartTime", period_start),
            QueryParameter.date_type("EndTime", period_end),
        ],
    )
    return [InternalTokenTransfer.from_dict(row) for row in data_set]


class TestDuneAnalytics(unittest.TestCase):
    def setUp(self):
        self.dune_connection = DuneAnalytics.new_from_environment()
        self.period_start = datetime.strptime("2022-03-01", "%Y-%m-%d")
        self.period_end = datetime.strptime("2022-03-15", "%Y-%m-%d")

    def test_one_buffer_trade(self):
        """
        tx: 0xd6b85ada980d10a11a5b6989c72e0232015ce16e7331524b38180b85f1aea6c8
        This transaction has 1 buffer trade wNXM for Ether
        """
        internal_transfers = get_internal_transfers(
            dune=self.dune_connection,
            tx_hash="0xd6b85ada980d10a11a5b6989c72e0232015ce16e7331524b38180b85f1aea6c8",
            period_start=self.period_start,
            period_end=self.period_end,
        )
        internal_trades = InternalTokenTransfer.internal_trades(internal_transfers)
        self.assertEqual(len(internal_trades), 1 * 2)
        # We had 0.91 USDT positive slippage
        print(internal_trades)
        self.assertEqual(
            token_slippage(
                "0xA0b86991c6218b36c1d19D4a2e9Eb0cE3606eB48", internal_transfers
            ),
            916698,
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
        internal_transfers = get_internal_transfers(
            dune=self.dune_connection,
            tx_hash="0x9a318d1abd997bcf8afed55b2946a7b1bd919d227f094cdcc99d8d6155808d7c",
            period_start=self.period_start,
            period_end=self.period_end,
        )
        internal_trades = InternalTokenTransfer.internal_trades(internal_transfers)
        self.assertEqual(len(internal_trades), 1 * 2)

    def test_does_not_recognize_selling_too_much_and_buying_too_much_as_internal_trade(
        self,
    ):
        """
        tx: 0x63e234a1a0d657f5725817f8d829c4e14d8194fdc49b5bc09322179ff99619e7
        In this transaction, the solver sells too much USDC and buys to much ETH.
        These trades could be seen as buffer trades, but they should not:
        These kind of trades can drain the buffers over time, as the prices of trading
        includes the AMM fees and hence are unfavourable for the buffers. Also, they are avoidable
        by using buyOrder on the AMMs.
        """
        internal_transfers = get_internal_transfers(
            dune=self.dune_connection,
            tx_hash="0x63e234a1a0d657f5725817f8d829c4e14d8194fdc49b5bc09322179ff99619e7",
            period_start=self.period_start,
            period_end=self.period_end,
        )
        internal_trades = InternalTokenTransfer.internal_trades(internal_transfers)
        self.assertEqual(len(internal_trades), 0 * 2)

    def test_does_filter_out_SOR_internal_trades_with_amm_interactions(self):
        """
        tx: 0x0ae4775b0a352f7ba61f5ec301aa6ac4de19b43f90d8a8674b6e5c8116eda96b
        In this transaction, the solver sells too much XFT and buys to much DAI. Usually
        this would be seen as a internal buffer trade, as the amounts match perfectly and DAI is in the allowed buffer token list.
        But, since the solution is coming from 0x, we know that it is not an internal buffer trade,
        given that the settlement had also an AMM interaction.
        """
        internal_transfers = get_internal_transfers(
            dune=self.dune_connection,
            tx_hash="0x0ae4775b0a352f7ba61f5ec301aa6ac4de19b43f90d8a8674b6e5c8116eda96b",
            period_start=self.period_start,
            period_end=self.period_end,
        )
        internal_trades = InternalTokenTransfer.internal_trades(internal_transfers)
        self.assertEqual(len(internal_trades), 0 * 2)
        self.assertEqual(
            token_slippage(
                "0x6B175474E89094C44Da98b954EedeAC495271d0F", internal_transfers
            ),
            4494166090057377749,
        )

    def test_does_recognize_slippage_due_to_buffer_token_list(self):
        """
        tx: 0x0bd527494e8efbf4c3013d1e355976ed90fa4e3b79d1f2c2a2690b02baae4abe
        This tx has a internal trade between pickle and eth. As pickle is not in the allow-list,
        the internal trade was not allowed.
        Our queries should recognized these kind of trades as slippage and not as a internal trades.
        """
        internal_transfers = get_internal_transfers(
            dune=self.dune_connection,
            tx_hash="0x0bd527494e8efbf4c3013d1e355976ed90fa4e3b79d1f2c2a2690b02baae4abe",
            period_start=self.period_start,
            period_end=self.period_end,
        )
        internal_trades = InternalTokenTransfer.internal_trades(internal_transfers)
        self.assertEqual(len(internal_trades), 0 * 2)
        self.assertEqual(
            token_slippage(
                "0xC02aaA39b223FE8D0A0e5C4F27eAD9083C756Cc2", internal_transfers
            ),
            -678305196269132000,
        )

    def test_deals_with_several_clearing_prices_for_same_token(self):
        """
        tx: 0x0d3a6219b26a180594278beeba745444010367401c347cf79f7b2385c308b2c9
        In some solutions, the clearing prices of the auctions are not unique, due to
        liquidity orders. In this case, we must sure that we don't duplicate internal buffer trades,
        due to a duplication of the rows. The upper tx is one example, where it previously happend.
        """
        internal_transfers = get_internal_transfers(
            dune=self.dune_connection,
            tx_hash="0x0d3a6219b26a180594278beeba745444010367401c347cf79f7b2385c308b2c9",
            period_start=self.period_start,
            period_end=self.period_end,
        )
        internal_trades = InternalTokenTransfer.internal_trades(internal_transfers)
        self.assertEqual(len(internal_trades), 1 * 2)

    def test_zero_buffer_trade(self):
        """
        tx: 0x31ab7acdadc65944a3f9507793ba9c3c58a1add35de338aa840ac951a24dc5bc
        Although there are two quite similar trades TOKE for ETH,
        the script should **not** detect a buffer trade
        """
        internal_transfers = get_internal_transfers(
            dune=self.dune_connection,
            tx_hash="0x31ab7acdadc65944a3f9507793ba9c3c58a1add35de338aa840ac951a24dc5bc",
            period_start=self.period_start,
            period_end=self.period_end,
        )
        internal_trades = InternalTokenTransfer.internal_trades(internal_transfers)
        self.assertEqual(len(internal_trades), 0 * 2)

    def test_buffer_trade_with_missing_price_from_pricesUSD(self):
        """
        tx: 0x80ae1c6a5224da60a1bf188f2101bd154e29ef71d54d136bfd1f6cc529f9d7ef
        CRVCX is not part of the price list
        """
        internal_transfers = get_internal_transfers(
            dune=self.dune_connection,
            tx_hash="0x80ae1c6a5224da60a1bf188f2101bd154e29ef71d54d136bfd1f6cc529f9d7ef",
            period_start=self.period_start,
            period_end=self.period_end,
        )
        internal_trades = InternalTokenTransfer.internal_trades(internal_transfers)

        self.assertEqual(len(internal_trades), 1 * 2)
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

    def test_buffer_trade_without_gp_settlement_price(self):
        """
        tx: 0x20ae31d11dba93d372ecf9d0cb387ea446e88572ce2d3d8e3d410871cfe6ec49
        This settlement has an internal tx between WETH and FOLD,
        but there are no settlement prices for WETH in the call data
        """
        internal_transfers = get_internal_transfers(
            dune=self.dune_connection,
            tx_hash="0x20ae31d11dba93d372ecf9d0cb387ea446e88572ce2d3d8e3d410871cfe6ec49",
            period_start=self.period_start,
            period_end=self.period_end,
        )
        internal_trades = InternalTokenTransfer.internal_trades(internal_transfers)
        self.assertEqual(len(internal_trades), 1 * 2)

    def test_it_recognizes_slippage(self):
        """
        tx: 0x703474ed43faadc35364254e4f9448e275c7cfe9cf60beddbdd68a462bf7f433
        Paraswap returns to little UST, but our buffers make up for it
        """
        internal_transfers = get_internal_transfers(
            dune=self.dune_connection,
            tx_hash="0x703474ed43faadc35364254e4f9448e275c7cfe9cf60beddbdd68a462bf7f433",
            period_start=self.period_start,
            period_end=self.period_end,
        )
        # We lost 58 UST dollars:
        self.assertEqual(
            token_slippage(
                "0xa47c8bf37f92aBed4A126BDA807A7b7498661acD", internal_transfers
            ),
            -57980197374074949357,
        )
        internal_trades = InternalTokenTransfer.internal_trades(internal_transfers)
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
        internal_transfers = get_internal_transfers(
            dune=self.dune_connection,
            tx_hash="0x07e91a80955eac0ea2292efe13fa694aea9ba5ae575ced8532e61d5e4806e8b4",
            period_start=self.period_start,
            period_end=self.period_end,
        )
        internal_trades = InternalTokenTransfer.internal_trades(internal_transfers)
        self.assertEqual(len(internal_trades), 0 * 2)


if __name__ == "__main__":
    unittest.main()
