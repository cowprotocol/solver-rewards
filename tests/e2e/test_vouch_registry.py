import unittest

from duneapi.api import DuneAPI

from src.fetch.reward_targets import get_raw_vouches, vouch_query


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


def test_vouch_events(events: list[str]) -> str:
    events.append(
        "(99999, 0, '\\xff'::bytea, '\\xff'::bytea, '\\xff'::bytea, '\\xff'::bytea)"
    )
    return event_str(events)


def test_invalidation_events(events: list[str]) -> str:
    events.append("(99999, 0, '\\xff'::bytea, '\\xff'::bytea, '\\xff'::bytea)")
    return event_str(events)


def vouch(
    block: int,
    evt_index: int,
    solver: int,
    pool: int,
    reward_target: int,
    sender: int,
) -> str:
    solver = solver_from(solver)
    target = target_from(reward_target)
    pool = pool_from(pool)
    sender = sender_from(sender)
    return f"({block}, {evt_index}, '{solver}'::bytea, '{target}'::bytea, '{pool}'::bytea, '{sender}'::bytea)"


def invalidate_vouch(
    block: int, evt_index: int, solver: int, pool: int, sender: int
) -> str:
    solver = solver_from(solver)
    pool = pool_from(pool)
    sender = sender_from(sender)
    return (
        f"({block}, {evt_index}, '{solver}'::bytea, '{pool}'::bytea, '{sender}'::bytea)"
    )


def vouch_query_from(vouches, invalidations) -> str:
    return vouch_query(
        vouch_events=test_vouch_events(vouches),
        invalidation_events=test_invalidation_events(invalidations),
        bonding_pools=TEST_BONDING_POOLS,
    )


class TestVouchRegistry(unittest.TestCase):
    def setUp(self) -> None:
        self.dune = DuneAPI.new_from_environment()

    def test_case_0(self):
        # vouch for same solver, two different pools then invalidate the first
        vouches = [
            vouch(0, 1, solver=0, pool=0, reward_target=0, sender=0),
            vouch(1, 1, solver=0, pool=1, reward_target=1, sender=1),
        ]
        fetched_records = get_raw_vouches(
            self.dune, raw_query=vouch_query_from(vouches, [])
        )
        self.assertEqual(len(fetched_records), 1)
        self.assertEqual(
            fetched_records[0],
            # First Vouch is the valid one!
            {
                "pool": pool_from(0),
                "reward_target": target_from(0),
                "solver": solver_from(0),
            },
        )

        # Now we add the invalidation of the first pool
        invalidations = [invalidate_vouch(3, 0, 0, 0, 0)]

        fetched_records = get_raw_vouches(
            self.dune, raw_query=vouch_query_from(vouches, invalidations)
        )
        self.assertEqual(len(fetched_records), 1)

        self.assertEqual(
            fetched_records[0],
            # Now the second vouch is the valid one!
            {
                "pool": pool_from(1),
                "reward_target": target_from(1),
                "solver": solver_from(0),
            },
        )


if __name__ == "__main__":
    unittest.main()
