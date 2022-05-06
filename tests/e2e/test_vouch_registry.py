import unittest

from duneapi.api import DuneAPI

from src.fetch.reward_targets import get_vouches, vouch_query

TEST_BONDING_POOLS = [
    "('\\xb0'::bytea, 'Pool 0', '\\xf0'::bytea)",
    "('\\xb1'::bytea, 'Pool 1', '\\xf1'::bytea)",
    "('\\xb2'::bytea, 'Pool 2', '\\xf2'::bytea)",
    "('\\xb3'::bytea, 'Pool 3', '\\xf3'::bytea)",
    "('\\xb4'::bytea, 'Pool 4', '\\xf4'::bytea)",
    "('\\xb5'::bytea, 'Pool 5', '\\xf5'::bytea)"
]


def test_events(events: list[str]) -> str:
    return f"select * from ( values {','.join(events)}) as _"

def vouch(
        block_number: int,
        evt_index: int,
        solver: int,
        pool: int,
        reward_target: int,
        sender: int
) -> str:
    solver_str = ''
    return f"({block_number}, {evt_index}, '\\x50'::bytea, '\\xc1'::bytea, '\\xb0'::bytea, '\\xf0'::bytea)"

class TestVouchRegistry(unittest.TestCase):
    def test_case_0(self):
        # vouch for same solver, two different pools then invalidate the first
        # (0, 0, '\x50'::bytea, '\xc1'::bytea, '\xb0'::bytea, '\xf0'::bytea), -- vouch(solver0, pool0)
        # (1, 0, '\x50'::bytea, '\xc1'::bytea, '\xb1'::bytea, '\xf1'::bytea),  -- vouch(solver0, pool1)
        vouches = [
            "(0, 0, '\\x50'::bytea, '\\xc1'::bytea, '\\xb0'::bytea, '\\xf0'::bytea)",
            "(1, 0, '\\x50'::bytea, '\\xc1'::bytea, '\\xb1'::bytea, '\\xf1'::bytea)"
        ]
        invalidations = [
            "(3, 0, '\\x50'::bytea, '\\xb0'::bytea, '\\xf0'::bytea)"
        ]

        query = vouch_query(
            vouch_events=test_events(vouches),
            invalidation_events=test_events(invalidations),
            bonding_pools=TEST_BONDING_POOLS
        )
        dune = DuneAPI.new_from_environment()
        get_vouches(dune, query)


if __name__ == "__main__":
    unittest.main()
