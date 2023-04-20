import {
  bigIntMapToJSON,
  getDB,
  hexToBytea,
  insertSettlementEvent,
  insertSettlementSimulations,
  insertTokenImbalances,
  jsonFromSettlementData,
} from "../src/database";
import * as process from "process";
import { sql } from "@databases/pg";
import ConnectionPool from "@databases/pg/lib/ConnectionPool";
import { SettlementSimulationData } from "../src/accounting";
import { ethers } from "ethers";

// Tried to use their Testing Docs, but it didn't seem quite right
// https://www.atdatabases.org/docs/pg-test

const dbURL: string =
  process.env["DATABASE_URL"] ||
  "postgresql://postgres:postgres@localhost:5432/postgres";
const db = getDB(dbURL);
const zeroHex = ethers.ZeroAddress;

describe("test database insertion methods", () => {
  beforeEach(async () => {
    await db.query(sql`TRUNCATE TABLE settlements;`);
    await db.query(sql`TRUNCATE TABLE internalized_imbalances;`);
    await db.query(sql`TRUNCATE TABLE settlement_simulations;`);
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
  test("insertSimulations(datum) & idempotent", async () => {
    const blockNumber = 1;
    const largeBigInt = 99999999999999999999999999999999999999999999999999n;
    const exampleLog = {
      address: zeroHex,
      // The indexed topics from the event log
      topics: [zeroHex, zeroHex],
      data: zeroHex,
    };
    const exampleEthDelta = new Map([["0x2", largeBigInt]]);
    const dummySimData: SettlementSimulationData = {
      txHash: zeroHex,
      full: {
        blockNumber,
        logs: [exampleLog, exampleLog],
        ethDelta: exampleEthDelta,
      },
      reduced: {
        blockNumber,
        logs: [exampleLog],
        ethDelta: exampleEthDelta,
      },
      winningSettlement: {
        solver: zeroHex,
        simulationBlock: blockNumber,
        reducedCallData: zeroHex,
        fullCallData: zeroHex,
      },
    };
    await insertSettlementSimulations(db, dummySimData);

    let results = await db.query(sql`SELECT * from settlement_simulations;`);
    const expected = [
      {
        complete: {
          blockNumber: blockNumber,
          ethDelta: bigIntMapToJSON(exampleEthDelta),
          logs: [exampleLog, exampleLog],
        },
        reduced: {
          blockNumber: blockNumber,
          ethDelta: bigIntMapToJSON(exampleEthDelta),
          logs: [exampleLog],
        },
        tx_hash: hexToBytea(zeroHex),
        winning_settlement: {
          fullCallData: zeroHex,
          reducedCallData: zeroHex,
          simulationBlock: blockNumber,
          solver: zeroHex,
        },
      },
    ];
    expect(results).toStrictEqual(expected);

    // Idempotency
    await insertSettlementSimulations(db, dummySimData);
    results = await db.query(sql`SELECT * from settlement_simulations;`);
    expect(results).toStrictEqual(expected);
  });
});

describe("jsonFromSettlementData", () => {
  afterAll(async () => {
    await (db as ConnectionPool).dispose();
  });

  test("converts settlement data to database object format", async () => {
    const blockNumber = 1;
    const bigNumber = 12345678910999999999999n;
    const dummySimData = {
      blockNumber,
      logs: [
        {
          address: zeroHex,
          // The indexed topics from the event log
          topics: [zeroHex],
          data: zeroHex,
        },
      ],
      ethDelta: new Map([["0x1", bigNumber]]),
    };
    jsonFromSettlementData(dummySimData);
    expect(jsonFromSettlementData(dummySimData)).toStrictEqual({
      blockNumber: 1,
      ethDelta: {
        "0x1": bigNumber.toString(),
      },
      logs: [
        {
          address: zeroHex,
          data: zeroHex,
          topics: [zeroHex],
        },
      ],
    });
  });
});
