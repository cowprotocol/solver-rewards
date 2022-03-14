import unittest
from datetime import datetime

from src.dune_analytics import DuneAnalytics, QueryParameter
from src.file_io import File
from src.models import Address, InternalTokenTransfer, Network


def token_slippage(
        token_str: str,
        internal_trade_list: list[InternalTokenTransfer],
) -> int:
    return sum(
        a.amount for a in internal_trade_list
        if a.token == Address(token_str)
    )


def get_internal_transfers(
        dune: DuneAnalytics,
        tx_hash: str,
        period_start: datetime,
        period_end: datetime
) -> list[InternalTokenTransfer]:
    path = "./queries/slippage"
    slippage_subquery = File(path=path,
                             name="subquery_batchwise_internal_transfers.sql")
    select_transfers_file = File(path=path, name="select_in_out_with_buffers.sql")
    query = "\n".join(
        [
            dune.open_query(slippage_subquery.filename()),
            dune.open_query(select_transfers_file.filename())
        ]
    )
    data_set = dune.fetch(
        query_str=query,
        network=Network.MAINNET,
        name='Internal Token Transfer Accounting',
        parameters=[
            QueryParameter.text_type('TxHash', tx_hash),
            QueryParameter.date_type("StartTime", period_start),
            QueryParameter.date_type("EndTime", period_end),
        ])
    return [
        InternalTokenTransfer.from_dict(row) for row in data_set
    ]


class TestDuneAnalytics(unittest.TestCase):
    def setUp(self):
        self.dune_connection = DuneAnalytics.new_from_environment()
        self.period_start = datetime.strptime('2022-03-01', "%Y-%m-%d")
        self.period_end = datetime.strptime('2022-03-12', "%Y-%m-%d")

    def test_one_buffer_trade(self):
        """
        tx: 0xd6b85ada980d10a11a5b6989c72e0232015ce16e7331524b38180b85f1aea6c8
        This transaction has 1 buffer trades wNXM for Ether
        """
        internal_transfers = get_internal_transfers(
            dune=self.dune_connection,
            tx_hash='0xd6b85ada980d10a11a5b6989c72e0232015ce16e7331524b38180b85f1aea6c8',
            period_start=self.period_start,
            period_end=self.period_end,
        )
        internal_trades = InternalTokenTransfer.internal_trades(internal_transfers)
        self.assertEqual(len(internal_trades), 1 * 2)
        # We had 0.91 USDT positive slippage
        print(internal_trades)
        self.assertEqual(
            token_slippage(
                '0xA0b86991c6218b36c1d19D4a2e9Eb0cE3606eB48',
                internal_transfers
            ), 916698)

    def test_zero_buffer_trade(self):
        """
        tx: 0x31ab7acdadc65944a3f9507793ba9c3c58a1add35de338aa840ac951a24dc5bc
        Although there are two quite similar trades TOKE for ETH,
        the script should **not** detect a buffer trade
        """
        internal_transfers = get_internal_transfers(
            dune=self.dune_connection,
            tx_hash='0x31ab7acdadc65944a3f9507793ba9c3c58a1add35de338aa840ac951a24dc5bc',
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
            tx_hash='0x80ae1c6a5224da60a1bf188f2101bd154e29ef71d54d136bfd1f6cc529f9d7ef',
            period_start=self.period_start,
            period_end=self.period_end,
        )
        internal_trades = InternalTokenTransfer.internal_trades(internal_transfers)

        self.assertEqual(len(internal_trades), 1 * 2)
        self.assertEqual(
            token_slippage(
                '0xD533a949740bb3306d119CC777fa900bA034cd52',
                internal_transfers
            ), 0)
        self.assertEqual(
            token_slippage(
                '0x62B9c7356A2Dc64a1969e19C23e4f579F9810Aa7',
                internal_transfers
            ), 0)

    def test_buffer_trade_without_gp_settlement_price(self):
        """
        tx: 0x20ae31d11dba93d372ecf9d0cb387ea446e88572ce2d3d8e3d410871cfe6ec49
        This settlement has an internal tx between WETH and FOLD,
        but there are no settlement prices for WETH in the call data
        """
        internal_transfers = get_internal_transfers(
            dune=self.dune_connection,
            tx_hash='0x20ae31d11dba93d372ecf9d0cb387ea446e88572ce2d3d8e3d410871cfe6ec49',
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
            tx_hash='0x703474ed43faadc35364254e4f9448e275c7cfe9cf60beddbdd68a462bf7f433',
            period_start=self.period_start,
            period_end=self.period_end,
        )
        internal_trades = InternalTokenTransfer.internal_trades(internal_transfers)
        self.assertEqual(len(internal_trades), 0 * 2)
        # We lost 58 UST dollars:
        self.assertEqual(
            token_slippage(
                '0xa47c8bf37f92aBed4A126BDA807A7b7498661acD',
                internal_transfers
            ), -57980197374074949357)

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
            tx_hash='0x07e91a80955eac0ea2292efe13fa694aea9ba5ae575ced8532e61d5e4806e8b4',
            period_start=self.period_start,
            period_end=self.period_end,
        )
        internal_trades = InternalTokenTransfer.internal_trades(internal_transfers)
        self.assertEqual(len(internal_trades), 0 * 2)


if __name__ == '__main__':
    unittest.main()
