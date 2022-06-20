import unittest
from datetime import datetime

from duneapi.api import DuneAPI
from duneapi.types import Address

from src.fetch.reward_targets import get_vouches, Vouch


class TestVouchRegistry(unittest.TestCase):
    def setUp(self) -> None:
        self.dune = DuneAPI.new_from_environment()

    def test_real_data(self):
        may_fifth = datetime.strptime("2022-05-05", "%Y-%m-%d")
        fetched_records = get_vouches(self.dune, end_time=may_fifth)
        solvers = [
            Address("\\x109bf9e0287cc95cc623fbe7380dd841d4bdeb03"),
            Address("\\x6fa201c3aff9f1e4897ed14c7326cf27548d9c35"),
        ]
        reward_target = Address("\\x84dbae2549d67caf00f65c355de3d6f4df59a32c")
        bonding_pool = Address("\\x5d4020b9261f01b6f8a45db929704b0ad6f5e9e6")
        self.assertEqual(
            list(fetched_records.values()),
            [
                Vouch(
                    solver=solvers[0],
                    bonding_pool=bonding_pool,
                    reward_target=reward_target,
                ),
                Vouch(
                    solver=solvers[1],
                    bonding_pool=bonding_pool,
                    reward_target=reward_target,
                ),
            ],
        )


if __name__ == "__main__":
    unittest.main()
