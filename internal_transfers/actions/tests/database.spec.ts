import {
  getDB,
  hexToBytea,
  insertSettlementEvent,
  insertTokenImbalances,
} from "../src/database";
import * as process from "process";
import { sql } from "@databases/pg";
import ConnectionPool from "@databases/pg/lib/ConnectionPool";

// Tried to use their Testing Docs, but it didn't seem quite right
// https://www.atdatabases.org/docs/pg-test

const dbURL: string =
  process.env["DATABASE_URL"] ||
  "postgresql://postgres:postgres@localhost:5432/postgres";
const db = getDB(dbURL);

describe("test database insertion methods", () => {
  beforeEach(async () => {
    await db.query(sql`TRUNCATE TABLE settlements;`);
    await db.query(sql`TRUNCATE TABLE internalized_imbalances;`);
  });

  afterAll(async () => {
    await (db as ConnectionPool).dispose();
  });

  test("insertSettlementEvent(txHash, solver)", async () => {
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
  test("insertImbalances(txHash, imbalances) & idempotent", async () => {
    const txHash = "0x4321";
    const token1 = "0x12";
    const token2 = "0x34";
    const imbalances = [
      {
        token: token1,
        amount:
          115792089237316195423570985008687907853269984665640564039457584007913129639935n,
      },
      { token: token2, amount: 5678n },
    ];
    await insertTokenImbalances(db, txHash, imbalances);

    let results = await db.query(sql`SELECT * from internalized_imbalances;`);
    const expectedResults = [
      {
        token: hexToBytea(token1),
        amount:
          "115792089237316195423570985008687907853269984665640564039457584007913129639935",
        tx_hash: hexToBytea(txHash),
      },
      {
        token: hexToBytea(token2),
        amount: "5678",
        tx_hash: hexToBytea(txHash),
      },
    ];
    expect(results).toStrictEqual(expectedResults);

    // Idempotency
    await insertTokenImbalances(db, txHash, imbalances);
    results = await db.query(sql`SELECT * from internalized_imbalances;`);
    expect(results).toStrictEqual(expectedResults);
  });
});
