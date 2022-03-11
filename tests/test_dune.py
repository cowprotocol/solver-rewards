import unittest
from unittest.mock import MagicMock, Mock

from src.dune_analytics import DuneAnalytics
from src.models import Network


class TestDuneAnalytics(unittest.TestCase):
    def test_retry(self):
        dune = DuneAnalytics('user', 'password', 0)
        dune.execute_and_await_results = MagicMock(return_value=1)
        dune.initiate_new_query = MagicMock(return_value=None)
        dune.open_query = MagicMock(return_value="")

        with self.assertRaises(Exception):
            dune.query_initiate_execute_await(
                query_str="",
                network=Network.MAINNET,
                max_retries=0
            )

        self.assertEqual(
            dune.query_initiate_execute_await(
                query_str="",
                network=Network.MAINNET,
                max_retries=1
            ), 1)

        dune.execute_and_await_results = Mock(side_effect=Exception("Max retries"))
        with self.assertRaises(Exception):
            dune.query_initiate_execute_await(
                query_str="",
                network=Network.MAINNET,
                max_retries=2
            )


if __name__ == '__main__':
    unittest.main()
