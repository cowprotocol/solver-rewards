import unittest

from duneapi.api import DuneAPI

from src.fetch.period_slippage import get_period_slippage
from src.models import AccountingPeriod


class TestDuneAnalytics(unittest.TestCase):
    def test_no_solver_has_huge_slippage_values(self):
        """
        This test makes sure that no solver had big slippage (bigger than 2 ETH).
        High slippage indicates that something significant is missing, but for sure
        I could happen that a solver has higher slippage than 2 ETH. In this case,
        there should be manual investigations
        """
        dune = DuneAPI.new_from_environment()
        solver_slippages = get_period_slippage(
            dune=dune, period=AccountingPeriod("2022-03-01", 1)
        )
        self.assertLess(
            solver_slippages.sum_positive() - solver_slippages.sum_negative(),
            2 * 10**18,
        )


if __name__ == "__main__":
    unittest.main()
