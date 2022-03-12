import unittest
from unittest.mock import MagicMock, Mock
from datetime import datetime


from src.dune_analytics import DuneAnalytics, QueryParameter
from src.fetch.transfer_file import Transfer
from src.models import Address, InternalTokenTransfer, Network, SolverSlippage
from tests.e2e.test_e2e_slippage_investigation import get_slippage_accounting


class TestDuneAnalytics(unittest.TestCase):
    def test_no_solver_has_huge_slippage_values(self):
        '''
            This test makes sure that no solver had big slippage (bigger than 2 ETH).
            High slippage indicates that something significant is missing, but for sure
            I could happen that a solver has higher slippage than 2 ETH. In this case,
            there should be manual investigations
        '''
        dune_connection = DuneAnalytics.new_from_environment()
        query_str = dune_connection.open_query("./queries/slippage/internal_token_transfers_for_settlements.sql") + "," + \
            dune_connection.open_query(
            "./queries/slippage/evaluate_slippage_from_internal_token_transfers.sql")
        slippage_accounting = get_slippage_accounting(
            dune=dune_connection,
            query_str=query_str,
            period_start=datetime.strptime('2022-03-10', "%Y-%m-%d"),
            period_end=datetime.strptime('2022-03-11', "%Y-%m-%d"),
        )
        assert(len(slippage_accounting) > 0)
        for obj in slippage_accounting:
            assert(abs(obj['eth_slippage_wei']) < 2*10**18)


if __name__ == '__main__':
    unittest.main()
