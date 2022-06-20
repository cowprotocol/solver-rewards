import unittest
from dataclasses import dataclass

from duneapi.types import DuneQuery, Network, QueryParameter

from src.fetch.reward_targets import vouch_query

from tests.db.pg_client import (
    ConnectionType,
    DBRouter,
    populate_from,
)


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


@dataclass
class MetaData:
    schema: str
    table: str
    fields: list[str]


# TODO - this can be part of the ORM i.e. the data classes modeling table records
VOUCH_META = MetaData(
    schema="cow_protocol",
    table="VouchRegister_evt_Vouch",
    fields=[
        "solver",
        '"bondingPool"',
        '"cowRewardTarget"',
        "sender",
        "evt_index",
        "evt_block_number",
    ],
)
INVALIDATION_META = MetaData(
    schema="cow_protocol",
    table="VouchRegister_evt_InvalidateVouch",
    fields=[
        "solver",
        '"bondingPool"',
        "sender",
        "evt_index",
        "evt_block_number",
    ],
)


# def event_str(events: list[str]) -> str:
#     event_string = ",\n        ".join(events)
#     return f"select * from (values {event_string}) as _"


def insert_query(meta: MetaData, events: list[str]) -> str:
    # TODO - pass in list[ProperTypes] instead of strings.
    values = ",".join(events)
    fields = f'({",".join(meta.fields)})'
    return f'INSERT INTO {meta.schema}."{meta.table}"{fields} (values {values});'


def vouch(
    block: int,
    evt_index: int,
    solver: str,
    pool: str,
    target: str,
    sender: str,
) -> str:
    return f"('{solver}'::bytea, '{pool}'::bytea, '{target}'::bytea, '{sender}'::bytea, {evt_index}, {block})"


def invalidate_vouch(
    block: int, evt_index: int, solver: str, pool: str, sender: str
) -> str:
    return (
        f"('{solver}'::bytea, '{pool}'::bytea, '{sender}'::bytea, {evt_index}, {block})"
    )


class TestVouchRegistry(unittest.TestCase):
    def setUp(self) -> None:
        self.dune = DBRouter(ConnectionType.LOCAL)
        populate_from(self.dune.cur, "./tests/db/schema_vouch_registry.sql")
        self.solvers = list(map(lambda t: solver_from(t), range(5)))
        self.pools = list(map(lambda t: pool_from(t), range(5)))
        self.targets = list(map(lambda t: target_from(t), range(5)))
        self.senders = list(map(lambda t: sender_from(t), range(5)))
        self.query = DuneQuery(
            raw_sql=vouch_query(bonding_pools=TEST_BONDING_POOLS),
            network=Network.MAINNET,
            name="Solver Reward Targets",
            parameters=[QueryParameter.date_type("EndTime", "2022-01-01 00:00:00")],
            query_id=-1,
            description="",
        )

    def tearDown(self) -> None:
        # self.dune.cur.execute(
        #     """
        # TRUNCATE cow_protocol."VouchRegister_evt_Vouch";
        # TRUNCATE cow_protocol."VouchRegister_evt_InvalidateVouch";
        # """
        # )
        self.dune.close()

    def test_invalidation_before_vouch(self):

        solver, sender, pool = self.solvers[0], self.senders[0], self.pools[0]
        target = self.targets[1]
        invalidations = [invalidate_vouch(0, 0, solver, pool, sender)]

        # Invalidation before Vouch
        self.dune.cur.execute(insert_query(INVALIDATION_META, invalidations))
        fetched_records = self.dune.fetch(self.query)

        # No vouches yet, so no records fetched.
        self.assertEqual(len(fetched_records), 0)

        vouches = [vouch(1, 0, solver, pool, target, sender)]
        self.dune.cur.execute(insert_query(VOUCH_META, vouches))
        fetched_records = self.dune.fetch(self.query)
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

    def test_vouch_for_same_solver_in_different_pools(self):
        # vouch for same solver, two different pools then invalidate the first
        solver = self.solvers[0]
        pool0, pool1 = self.pools[:2]
        target0, target1 = self.targets[:2]
        sender0, sender1 = self.senders[:2]
        self.dune.cur.execute(
            insert_query(
                meta=VOUCH_META,
                events=[
                    vouch(0, 1, solver, pool0, target0, sender0),
                    vouch(1, 1, solver, pool1, target1, sender1),
                ],
            )
        )
        fetched_records = self.dune.fetch(self.query)
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
        self.dune.cur.execute(
            insert_query(
                meta=INVALIDATION_META,
                events=[invalidate_vouch(3, 0, solver, pool0, sender0)],
            )
        )
        fetched_records = self.dune.fetch(self.query)
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

    def test_doesnt_recognize_vouch_from_invalid_sender(self):
        # Vouch from invalid sender:
        solver, pool, target = self.solvers[0], self.pools[0], self.targets[0]
        invalid_sender = self.senders[1]
        # Insert Vouch Records
        self.dune.cur.execute(
            insert_query(
                VOUCH_META, [vouch(0, 0, solver, pool, target, invalid_sender)]
            )
        )
        fetched_records = self.dune.fetch(self.query)
        self.assertEqual(len(fetched_records), 0)

    def test_update_cow_reward_target(self):
        # Vouch from invalid sender:
        solver, pool, sender = self.solvers[0], self.pools[0], self.senders[0]
        target0, target1 = self.targets[:2]
        self.dune.cur.execute(
            insert_query(
                meta=VOUCH_META,
                events=[
                    vouch(0, 0, solver, pool, target0, sender),
                    vouch(0, 1, solver, pool, target1, sender),
                ],
            )
        )
        fetched_records = self.dune.fetch(self.query)
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
