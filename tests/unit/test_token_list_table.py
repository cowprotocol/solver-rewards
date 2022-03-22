import unittest

from src.fetch.period_slippage import allowed_token_list_query, prepend_to_sub_query


class TestQueryBuilding(unittest.TestCase):
    def test_empty_token_list(self):
        with self.assertRaises(ValueError) as err:
            allowed_token_list_query([])
        self.assertEqual(str(err.exception), "Cannot build query for empty token list")

    def test_builds_intended_query(self):
        tokens = [
            "0xde1c59bc25d806ad9ddcbe246c4b5e5505645718",
            "0x111119bc25d806ad9ddcbe246c4b5e5505645718",
        ]
        expected_query = "allow_listed_tokens as (select * from (VALUES ('\\xde1c59bc25d806ad9ddcbe246c4b5e5505645718' :: bytea),('\\x111119bc25d806ad9ddcbe246c4b5e5505645718' :: bytea)) AS t (token)),"
        query = allowed_token_list_query(tokens)
        self.assertEqual(query, expected_query)

    def test_adds_table_after_with_statement(self):
        test_query = "WITH Select * from table"
        table_to_add = "table as (Select * from other_table)"
        result_query = prepend_to_sub_query(test_query, table_to_add)
        self.assertEqual(
            "WITH\ntable as (Select * from other_table)\nSelect * from table",
            result_query,
        )


if __name__ == "__main__":
    unittest.main()
