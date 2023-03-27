import { getDB, hexToBytea, insertSettlementEvent } from "../src/database";
import * as process from "process";
import { sql } from "@databases/pg";
import ConnectionPool from "@databases/pg/lib/ConnectionPool";

// Tried to use their Testing Docs, but it didn't seem quite right
// https://www.atdatabases.org/docs/pg-test

const dbURL: string =
  process.env["DATABASE_URL"] ||
  "postgresql://postgres:postgres@localhost:5432/postgres";
const db = getDB(dbURL);
describe("insertSettlementEvent(txHash, solver)", () => {
  beforeEach(async () => {
    await db.query(sql`TRUNCATE TABLE settlements;`);
  });

  afterAll(async () => {
    await (db as ConnectionPool).dispose();
  });

  test("Inserts to DB", async () => {
    const txHash =
      "0x45f52ee09622eac16d0fe27b90a76749019b599c9566f10e21e8d0955a0e428e";
    const solver = "0xc9ec550bea1c64d779124b23a26292cc223327b6";

    await insertSettlementEvent(
      db,
      { txHash: txHash, blockNumber: 0 },
      { solver: solver, logIndex: 0 }
    );

    const results = await db.query(sql`SELECT * from settlements;`);
    expect(results).toStrictEqual([
      {
        block_number: BigInt(0),
        log_index: BigInt(0),
        solver: hexToBytea(solver),
        tx_hash: hexToBytea(txHash),
      },
    ]);
  });
});
