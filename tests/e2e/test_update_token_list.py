import unittest

from duneapi.api import DuneAPI

from src.update.token_list import update_token_list


class TestTokenList(unittest.TestCase):
    def test_no_solver_has_huge_slippage_values(self):
        """
        This test makes sure that no solver had big slippage (bigger than 2 ETH).
        High slippage indicates that something significant is missing, but for sure
        I could happen that a solver has higher slippage than 2 ETH. In this case,
        there should be manual investigations
        """
        dune = DuneAPI.new_from_environment()
        update_token_list(dune)


if __name__ == "__main__":
    unittest.main()
