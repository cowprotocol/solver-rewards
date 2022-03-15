import unittest
from datetime import datetime

from src.dune_analytics import DuneAnalytics
from src.fetch.period_slippage import get_period_slippage


class TestDuneAnalytics(unittest.TestCase):
    def test_no_solver_has_huge_slippage_values(self):
        """
        This test makes sure that no solver had big slippage (bigger than 2 ETH).
        High slippage indicates that something significant is missing, but for sure
        I could happen that a solver has higher slippage than 2 ETH. In this case,
        there should be manual investigations
        """
        dune = DuneAnalytics.new_from_environment()
        slippage_accounting = get_period_slippage(
            dune=dune,
            period_start=datetime.strptime('2022-03-01', "%Y-%m-%d"),
            period_end=datetime.strptime('2022-03-14', "%Y-%m-%d"),
        )
        assert (len(slippage_accounting) > 0)
        for obj in slippage_accounting:
            assert (abs(obj['eth_slippage_wei']) < 2 * 10 ** 18)


if __name__ == '__main__':
    unittest.main()
