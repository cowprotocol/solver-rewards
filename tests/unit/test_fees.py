import unittest

from pandas import Series

from src.fetch.fees import (
    compute_trade_fee_datum,
    compute_surplus_protocol_fee,
    parse_recipient,
    parse_protocol_fee_kind,
)


class TestFees(unittest.TestCase):
    def test_parse_recipient(self):
        # normal result
        row = Series(
            {
                "app_data": "0x7b22617070436f6465223a2273686170657368696674222c226d65746164617461223a7b226f72646572436c617373223a7b226f72646572436c617373223a226d61726b6574227d2c22706172746e6572466565223a7b22627073223a34382c22726563697069656e74223a22307839306134386435636637333433623038646131326530363736383062346336646266653535316265227d2c2271756f7465223a7b22736c69707061676542697073223a223530227d7d2c2276657273696f6e223a22302e392e30227d"
            }
        )
        self.assertEqual(
            parse_recipient(row), "0x90a48d5cf7343b08da12e067680b4c6dbfe551be"
        )
        # no recipient
        row = Series({"app_data": "0x7b7d"})
        self.assertEqual(parse_recipient(row), None)
        # empty string
        row = Series({"app_data": "0x"})
        self.assertEqual(parse_recipient(row), None)

    def test_parse_protocol_fee_kind(self):
        row = Series({"protocol_fee_kind": "{fee_type}"})
        self.assertEqual(parse_protocol_fee_kind(row), ["fee_type"])

        row = Series({"protocol_fee_kind": "{fee_type_1,fee_type_2,fee_type_3}"})
        self.assertEqual(
            parse_protocol_fee_kind(row), ["fee_type_1", "fee_type_2", "fee_type_3"]
        )

    def test_compute_surplus_protocol_fee(self):
        # sell order
        row = Series(
            {
                "winning_solver": "0x0001",
                "auction_id": 0,
                "order_uid": "0x01",
                "kind": "sell",
                "sell_token": "0x000001",
                "buy_token": "0x000002",
                "limit_sell_amount": 100 * 10**18,
                "limit_buy_amount": 94 * 10**6,
                "quote_solver": None,
                "sell_token_native_price": 5 * 10**14,
                "buy_token_native_price": 5 * 10**26,
            }
        ).astype(object)
        sell_amount, buy_amount = 100 * 10**18, 95 * 10**6
        # not capped at volume
        surplus_factor = 0.5
        surplus_max_volume_factor = 0.05
        self.assertEqual(
            compute_surplus_protocol_fee(
                row, sell_amount, buy_amount, surplus_factor, surplus_max_volume_factor
            ),
            (
                1 * 10**6,
                "0x000002",
                5 * 10**26 / 10**18,
                100 * 10**18,
                96 * 10**6,
            ),
        )
        # capped at volume fee
        surplus_factor = 0.9
        surplus_max_volume_factor = 0.05
        self.assertEqual(
            compute_surplus_protocol_fee(
                row, sell_amount, buy_amount, surplus_factor, surplus_max_volume_factor
            ),
            (
                5 * 10**6,
                "0x000002",
                5 * 10**26 / 10**18,
                100 * 10**18,
                100 * 10**6,
            ),
        )

        # sbuy order
        row = Series(
            {
                "winning_solver": "0x0001",
                "auction_id": 0,
                "order_uid": "0x01",
                "kind": "buy",
                "sell_token": "0x000001",
                "buy_token": "0x000002",
                "limit_sell_amount": 106 * 10**18,
                "limit_buy_amount": 100 * 10**6,
                "quote_solver": None,
                "sell_token_native_price": 5 * 10**14,
                "buy_token_native_price": 5 * 10**26,
            }
        ).astype(object)
        sell_amount, buy_amount = 105 * 10**18, 100 * 10**6
        # not capped at volume
        surplus_factor = 0.5
        surplus_max_volume_factor = 0.05
        self.assertEqual(
            compute_surplus_protocol_fee(
                row, sell_amount, buy_amount, surplus_factor, surplus_max_volume_factor
            ),
            (
                1 * 10**18,
                "0x000001",
                5 * 10**14 / 10**18,
                104 * 10**18,
                100 * 10**6,
            ),
        )
        # capped at volume fee
        surplus_factor = 0.9
        surplus_max_volume_factor = 0.05
        self.assertEqual(
            compute_surplus_protocol_fee(
                row, sell_amount, buy_amount, surplus_factor, surplus_max_volume_factor
            ),
            (
                5 * 10**18,
                "0x000001",
                5 * 10**14 / 10**18,
                100 * 10**18,
                100 * 10**6,
            ),
        )

    def test_compute_price_improvement_protocol_fee(self):
        pass

    def test_compute_volume_protocol_fee(self):
        pass

    def test_compute_network_fee(self):
        pass

    def test_compute_trade_fee_datum(self):
        """Test computation of trade fees.
        This in particular tests the implementation of multiple fees.
        """

        def create_order(
            app_data,
            application_order,
            protocol_fee_kind,
            surplus_factor,
            surplus_max_volume_factor,
            volume_factor,
            price_improvement_factor,
            price_improvement_max_volume_factor,
        ):
            """Helper function for creating trades"""
            # pylint: disable-msg=too-many-arguments
            return Series(
                {
                    "winning_solver": "0x0001",
                    "auction_id": 0,
                    "order_uid": "0x01",
                    "kind": "sell",
                    "buy_token": "0x000001",
                    "limit_sell_amount": 100 * 10**18,
                    "limit_buy_amount": 94 * 10**6,
                    "app_data": app_data,
                    "quote_solver": None,
                    "sell_amount": 100 * 10**18,
                    "buy_amount": 95 * 10**6,
                    "observed_fee": 5 * 10**18,
                    "sell_token_native_price": 5 * 10**14,
                    "buy_token_native_price": 5 * 10**26,
                    "application_order": application_order,
                    "protocol_fee_kind": protocol_fee_kind,
                    "surplus_factor": surplus_factor,
                    "surplus_max_volume_factor": surplus_max_volume_factor,
                    "volume_factor": volume_factor,
                    "price_improvement_factor": price_improvement_factor,
                    "price_improvement_max_volume_factor": price_improvement_max_volume_factor,
                }
            ).astype(object)

        # no protocol fee
        app_data = "0x7b7d"
        application_order = None
        protocol_fee_kind = None
        surplus_factor = None
        surplus_max_volume_factor = None
        volume_factor = None
        price_improvement_factor = None
        price_improvement_max_volume_factor = None
        row = create_order(
            app_data,
            application_order,
            protocol_fee_kind,
            surplus_factor,
            surplus_max_volume_factor,
            volume_factor,
            price_improvement_factor,
            price_improvement_max_volume_factor,
        )
        trade_fee_datum = compute_trade_fee_datum(row)
        expected_trade_fee_datum = (
            0,
            "0x01",
            "0x0001",
            5 * 10**18 * 5 * 10**14 / 10**18,
            [],
            [],
            [],
            [],
            [],
            None,
        )
        self.assertEqual(trade_fee_datum, expected_trade_fee_datum)

        # one protocol fee
        app_data = "0x7b7d"
        application_order = [0]
        protocol_fee_kind = "{surplus}"
        surplus_factor = [0.5]
        surplus_max_volume_factor = [0.05]
        volume_factor = [None]
        price_improvement_factor = [None]
        price_improvement_max_volume_factor = [None]
        row = create_order(
            app_data,
            application_order,
            protocol_fee_kind,
            surplus_factor,
            surplus_max_volume_factor,
            volume_factor,
            price_improvement_factor,
            price_improvement_max_volume_factor,
        )
        trade_fee_datum = compute_trade_fee_datum(row)
        expected_trade_fee_datum = (
            0,
            "0x01",
            "0x0001",
            int(4 * 10**18 * 5 * 10**14 / 10**18),
            [1 * 10**6],
            ["0x000001"],
            [5 * 10**26 / 10**18],
            ["surplus"],
            [False],
            None,
        )
        self.assertEqual(trade_fee_datum, expected_trade_fee_datum)

        # multiple protocol fees
        app_data = "0x7b7d"
        application_order = [0, 1]
        protocol_fee_kind = "{surplus,volume}"
        surplus_factor = [0.5, None]
        surplus_max_volume_factor = [0.05, None]
        volume_factor = [None, 0.01]
        price_improvement_factor = [None, None]
        price_improvement_max_volume_factor = [None, None]
        row = create_order(
            app_data,
            application_order,
            protocol_fee_kind,
            surplus_factor,
            surplus_max_volume_factor,
            volume_factor,
            price_improvement_factor,
            price_improvement_max_volume_factor,
        )
        trade_fee_datum = compute_trade_fee_datum(row)
        expected_trade_fee_datum = (
            0,
            "0x01",
            "0x0001",
            int(
                (
                    100000000
                    - (
                        2
                        * (
                            int(95 * 10**6 * 0.01 / 0.99)
                            + 95 * 10**6
                            - 94 * 10**6
                        )
                        + 94 * 10**6
                    )
                )
                * 5
                * 10**26
                / 10**18
            ),
            [
                int(95 * 10**6 * 0.01 / 0.99) + 95 * 10**6 - 94 * 10**6,
                int(95 * 10**6 * 0.01 / 0.99),
            ],
            ["0x000001", "0x000001"],
            [5 * 10**26 / 10**18, 5 * 10**26 / 10**18],
            ["surplus", "volume"],
            [False, False],
            None,
        )
        self.assertEqual(trade_fee_datum, expected_trade_fee_datum)

        # multiple protocol fees and parter fee
        app_data = "0x7b22617070436f6465223a2273686170657368696674222c226d65746164617461223a7b226f72646572436c617373223a7b226f72646572436c617373223a226d61726b6574227d2c22706172746e6572466565223a7b22627073223a34382c22726563697069656e74223a22307839306134386435636637333433623038646131326530363736383062346336646266653535316265227d2c2271756f7465223a7b22736c69707061676542697073223a223530227d7d2c2276657273696f6e223a22302e392e30227d"
        application_order = [0, 1]
        protocol_fee_kind = "{surplus,volume}"
        surplus_factor = [0.5, None]
        surplus_max_volume_factor = [0.05, None]
        volume_factor = [None, 0.01]
        price_improvement_factor = [None, None]
        price_improvement_max_volume_factor = [None, None]
        row = create_order(
            app_data,
            application_order,
            protocol_fee_kind,
            surplus_factor,
            surplus_max_volume_factor,
            volume_factor,
            price_improvement_factor,
            price_improvement_max_volume_factor,
        )
        trade_fee_datum = compute_trade_fee_datum(row)
        expected_trade_fee_datum = (
            0,
            "0x01",
            "0x0001",
            int(
                (
                    100000000
                    - (
                        2
                        * (
                            int(95 * 10**6 * 0.01 / 0.99)
                            + 95 * 10**6
                            - 94 * 10**6
                        )
                        + 94 * 10**6
                    )
                )
                * 5
                * 10**26
                / 10**18
            ),
            [
                int(95 * 10**6 * 0.01 / 0.99) + 95 * 10**6 - 94 * 10**6,
                int(95 * 10**6 * 0.01 / 0.99),
            ],
            ["0x000001", "0x000001"],
            [5 * 10**26 / 10**18, 5 * 10**26 / 10**18],
            ["surplus", "volume"],
            [False, True],
            "0x90a48d5cf7343b08da12e067680b4c6dbfe551be",
        )
        self.assertEqual(trade_fee_datum, expected_trade_fee_datum)

        # error for non volume partner fee
        row = Series(
            {
                "auction_id": 0,
                "order_uid": "0x01",
                "winning_solver": "0x0001",
                "observed_fee": 10**18,
                "sell_token_native_price": 5 * 10**14,
                "protocol_fee_kind": "{surplus}",
                "app_data": "0x7b22617070436f6465223a2273686170657368696674222c226d65746164617461223a7b226f72646572436c617373223a7b226f72646572436c617373223a226d61726b6574227d2c22706172746e6572466565223a7b22627073223a34382c22726563697069656e74223a22307839306134386435636637333433623038646131326530363736383062346336646266653535316265227d2c2271756f7465223a7b22736c69707061676542697073223a223530227d7d2c2276657273696f6e223a22302e392e30227d",
            }
        ).astype(object)
        with self.assertRaises(ValueError):
            compute_trade_fee_datum(row)

    # TODO: Implement these tests, see issue #361
    def test_compute_trade_fees(self):
        pass

    def test_compute_total_fees(self):
        pass

    def test_compute_protocol_partner_fees(self):
        pass
