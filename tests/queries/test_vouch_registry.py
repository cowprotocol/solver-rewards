import unittest
from dataclasses import dataclass

<<<<<<< HEAD
from duneapi.types import DuneQuery, Address

from src.base_query import base_query, RECOGNIZED_BONDING_POOLS
from src.fetch.reward_targets import Vouch, parse_vouches
from src.models import AccountingPeriod
=======
from duneapi.types import DuneQuery, Network, QueryParameter, Address
from duneapi.util import open_query

from src.fetch.reward_targets import Vouch, parse_vouches, RECOGNIZED_BONDING_POOLS
>>>>>>> main
from tests.db.pg_client import (
    ConnectionType,
    DBRouter,
    populate_from,
)


def pool_from(num: int) -> str:
    return f"\\xb{num}"


def sender_from(num: int) -> str:
    return f"\\xf{num}"


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


def local_vouch_query(end_date: str, bonding_pools: list[str]) -> DuneQuery:
    return base_query(
        name="",
        select="select * from valid_vouches",
        period=AccountingPeriod.from_end(end_date),
        bonding_pools=bonding_pools,
        connection_type=ConnectionType.LOCAL,
    )


class TestVouchRegistry(unittest.TestCase):
    def setUp(self) -> None:
        self.dune = DBRouter(ConnectionType.LOCAL)
        self.solvers = list(map(lambda t: f"\\x5{t}", range(5)))
        self.pools = list(map(lambda t: pool_from(t), range(5)))
        self.targets = list(map(lambda t: f"\\xc{t}", range(5)))
        self.senders = list(map(lambda t: sender_from(t), range(5)))
        self.test_query = local_vouch_query("2022-01-01", TEST_BONDING_POOLS)

    def insert_vouches(self, vouches: list[str]):
        self.dune.cur.execute(insert_query(VOUCH_META, vouches))

    def insert_invalidations(self, invalidations: list[str]):
        self.dune.cur.execute(insert_query(INVALIDATION_META, invalidations))

    def tearDown(self) -> None:
        self.dune.close()

    def test_real_data(self):
        may_fifth = "2022-05-05"
        populate_from(self.dune.cur, "./tests/db/vouch_registry_real_data.sql")
        fetched_records = parse_vouches(
            self.dune.fetch(local_vouch_query(may_fifth, RECOGNIZED_BONDING_POOLS))
        )
        reward_target = Address("\\x84dbae2549d67caf00f65c355de3d6f4df59a32c")
        bonding_pool = Address("\\x5d4020b9261f01b6f8a45db929704b0ad6f5e9e6")

        self.assertEqual(
            list(fetched_records.values()),
            [
                Vouch(
                    solver=Address("\\x109bf9e0287cc95cc623fbe7380dd841d4bdeb03"),
                    bonding_pool=bonding_pool,
                    reward_target=reward_target,
                ),
                Vouch(
                    solver=Address("\\x6fa201c3aff9f1e4897ed14c7326cf27548d9c35"),
                    bonding_pool=bonding_pool,
                    reward_target=reward_target,
                ),
            ],
        )

    def test_invalidation_before_vouch(self):
        solver, sender, pool = self.solvers[0], self.senders[0], self.pools[0]
        target = self.targets[1]

        # Invalidation before Vouch
        self.insert_invalidations([invalidate_vouch(0, 0, solver, pool, sender)])
        fetched_records = self.dune.fetch(self.test_query)

        # No vouches yet, so no records fetched.
        self.assertEqual(len(fetched_records), 0)

        self.insert_vouches([vouch(1, 0, solver, pool, target, sender)])
        fetched_records = self.dune.fetch(self.test_query)
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
        self.insert_vouches(
            [
                vouch(0, 1, solver, pool0, target0, sender0),
                vouch(1, 1, solver, pool1, target1, sender1),
            ]
        )
        fetched_records = self.dune.fetch(self.test_query)
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
        self.insert_invalidations([invalidate_vouch(3, 0, solver, pool0, sender0)])
        fetched_records = self.dune.fetch(self.test_query)
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
        self.insert_vouches([vouch(0, 0, solver, pool, target, invalid_sender)])
        fetched_records = self.dune.fetch(self.test_query)
        self.assertEqual(len(fetched_records), 0)

    def test_update_cow_reward_target(self):
        # Vouch from invalid sender:
        solver, pool, sender = self.solvers[0], self.pools[0], self.senders[0]
        target0, target1 = self.targets[:2]
        self.insert_vouches(
            [
                vouch(0, 0, solver, pool, target0, sender),
                vouch(0, 1, solver, pool, target1, sender),
            ]
        )
        fetched_records = self.dune.fetch(self.test_query)
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
