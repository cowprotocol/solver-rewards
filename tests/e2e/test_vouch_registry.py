import unittest
from datetime import datetime

from duneapi.api import DuneAPI
from duneapi.types import Address

from src.fetch.reward_targets import get_raw_vouches, vouch_query, get_vouches, Vouch


def solver_from(num: int) -> str:
    return f"\\x5{num}"


def pool_from(num: int) -> str:
    return f"\\xb{num}"


def sender_from(num: int) -> str:
    return f"\\xf{num}"


def target_from(num: int) -> str:
    return f"\\xc{num}"


TEST_BONDING_POOLS = [
    f"('{pool_from(i)}'::bytea, 'Pool {i}', '{sender_from(i)}'::bytea)"
    for i in range(5)
]


def event_str(events: list[str]) -> str:
    event_string = ",\n        ".join(events)
    return f"select * from (values {event_string}) as _"


def mock_vouch_events(events: list[str]) -> str:
    # We have put one dummy invalid record to account for empty lists
    events.append(
        "(99999, 0, '\\xff'::bytea, '\\xff'::bytea, '\\xff'::bytea, '\\xff'::bytea)"
    )
    return event_str(events)


def mock_invalidation_events(events: list[str]) -> str:
    # We have put one dummy invalid record to account for empty lists
    events.append("(99999, 0, '\\xff'::bytea, '\\xff'::bytea, '\\xff'::bytea)")
    return event_str(events)


def vouch(
    block: int,
    evt_index: int,
    solver: str,
    pool: str,
    target: str,
    sender: str,
) -> str:
    return f"({block}, {evt_index}, '{solver}'::bytea, '{target}'::bytea, '{pool}'::bytea, '{sender}'::bytea)"


def invalidate_vouch(
    block: int, evt_index: int, solver: str, pool: str, sender: str
) -> str:
    return (
        f"({block}, {evt_index}, '{solver}'::bytea, '{pool}'::bytea, '{sender}'::bytea)"
    )


def vouch_query_from(vouches, invalidations) -> str:
    return vouch_query(
        vouch_events=mock_vouch_events(vouches),
        invalidation_events=mock_invalidation_events(invalidations),
        bonding_pools=TEST_BONDING_POOLS,
    )


class TestVouchRegistry(unittest.TestCase):
    def setUp(self) -> None:
        self.dune = DuneAPI.new_from_environment()
        self.solvers = list(map(lambda t: solver_from(t), range(5)))
        self.pools = list(map(lambda t: pool_from(t), range(5)))
        self.targets = list(map(lambda t: target_from(t), range(5)))
        self.senders = list(map(lambda t: sender_from(t), range(5)))

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

    def test_vouch_for_same_solver_in_different_pools(self):
        # vouch for same solver, two different pools then invalidate the first
        solver = self.solvers[0]
        pool0, pool1 = self.pools[:2]
        target0, target1 = self.targets[:2]
        sender0, sender1 = self.senders[:2]
        vouches = [
            vouch(0, 1, solver, pool0, target0, sender0),
            vouch(1, 1, solver, pool1, target1, sender1),
        ]
        fetched_records = get_raw_vouches(
            self.dune, raw_query=vouch_query_from(vouches, [])
        )
        self.assertEqual(len(fetched_records), 1)
        self.assertEqual(
            fetched_records[0],
            # First Vouch is the valid one!
            {
                "pool": pool0,
                "reward_target": target0,
                "solver": solver,
            },
        )

        # Now we add the invalidation of the first pool
        invalidations = [invalidate_vouch(3, 0, solver, pool0, sender0)]

        fetched_records = get_raw_vouches(
            self.dune, raw_query=vouch_query_from(vouches, invalidations)
        )
        self.assertEqual(len(fetched_records), 1)

        self.assertEqual(
            fetched_records[0],
            # Now the second vouch is the valid one!
            {
                "pool": pool1,
                "reward_target": target1,
                "solver": solver,
            },
        )

    def test_invalidation_before_vouch(self):
        # Invalidation before Vouch
        solver, sender, pool = self.solvers[0], self.senders[0], self.pools[0]
        target = self.targets[1]
        invalidations = [invalidate_vouch(0, 0, solver, pool, sender)]

        fetched_records = get_raw_vouches(
            self.dune, raw_query=vouch_query_from([], invalidations)
        )
        # No vouches yet, so no records fetched.
        self.assertEqual(len(fetched_records), 0)

        vouches = [
            vouch(1, 0, solver, pool, target, sender),
        ]
        fetched_records = get_raw_vouches(
            self.dune, raw_query=vouch_query_from(vouches, invalidations)
        )
        # Vouch has come in (after the invalidation), so it is a valid vouch
        self.assertEqual(len(fetched_records), 1)
        self.assertEqual(
            fetched_records[0],
            {
                "pool": pool,
                "reward_target": target,
                "solver": solver,
            },
        )

    def test_vouch_from_invalid_sender(self):
        # Vouch from invalid sender:
        solver, pool, target = self.solvers[0], self.pools[0], self.targets[0]
        invalid_sender = self.senders[1]
        fetched_records = get_raw_vouches(
            self.dune,
            raw_query=vouch_query_from(
                vouches=[vouch(0, 0, solver, pool, target, invalid_sender)],
                invalidations=[],
            ),
        )
        self.assertEqual(len(fetched_records), 0)

    def test_update_cow_reward_target(self):
        # Vouch from invalid sender:
        solver, pool, sender = self.solvers[0], self.pools[0], self.senders[0]
        target0, target1 = self.targets[:2]
        fetched_records = get_raw_vouches(
            self.dune,
            raw_query=vouch_query_from(
                vouches=[
                    vouch(0, 0, solver, pool, target0, sender),
                    vouch(0, 1, solver, pool, target1, sender),
                ],
                invalidations=[],
            ),
        )
        self.assertEqual(1, len(fetched_records))
        self.assertEqual(
            fetched_records[0],
            {
                "pool": pool,
                "reward_target": target1,
                "solver": solver,
            },
        )


if __name__ == "__main__":
    unittest.main()
