import {
  bigIntMapToJSON,
  getDB,
  hexToBytea,
  insertSettlementEvent,
  insertSettlementSimulations,
  insertTokenImbalances,
  jsonFromSettlementData,
  insertPipelineResults,
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

    const results = await db.query(sql`SELECT *
                                           from settlements;`);
    expect(results).toStrictEqual([
      {
        block_number: BigInt(0),
        log_index: BigInt(0),
        solver: hexToBytea(solver),
        tx_hash: hexToBytea(txHash),
      },
    ]);
  });
  test("insertImbalances(txHash, imbalances)", async () => {
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

    let results = await db.query(sql`SELECT *
                                         from internalized_imbalances;`);
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

    await expect(insertTokenImbalances(db, txHash, imbalances)).rejects.toThrow(
      'duplicate key value violates unique constraint "internalized_imbalances_pkey"'
    );
  });
  test("insertSimulations(datum) & idempotent", async () => {
    const blockNumber = 1;
    const gasUsed = 2;
    const simulationID = "sim-id";
    const largeBigInt = 99999999999999999999999999999999999999999999999999n;
    const exampleLog = {
      address: ethers.ZeroAddress,
      // The indexed topics from the event log
      topics: [ethers.ZeroHash, ethers.ZeroHash],
      data: ethers.ZeroHash,
    };
    const exampleEthDelta = new Map([["0x2", largeBigInt]]);
    const dummySimData: SettlementSimulationData = {
      txHash: ethers.ZeroHash,
      full: {
        simulationID,
        gasUsed,
        blockNumber,
        // Note there are 2 logs here!
        logs: [exampleLog, exampleLog],
        ethDelta: exampleEthDelta,
      },
      reduced: {
        simulationID,
        gasUsed,
        blockNumber,
        // and only 1 log here!
        logs: [exampleLog],
        ethDelta: exampleEthDelta,
      },
      winningSettlement: {
        solver: ethers.ZeroAddress,
        simulationBlock: blockNumber,
        reducedCallData: "0xca11da7a",
        fullCallData: "0xca11da7a000000",
      },
    };
    await insertSettlementSimulations(db, dummySimData);

    let results = await db.query(sql`SELECT *
                                         from settlement_simulations;`);
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
        tx_hash: hexToBytea(ethers.ZeroHash),
        winning_settlement: {
          fullCallData: "0xca11da7a000000",
          reducedCallData: "0xca11da7a",
          simulationBlock: blockNumber,
          solver: ethers.ZeroAddress,
        },
      },
    ];
    expect(results).toStrictEqual(expected);

    await expect(insertSettlementSimulations(db, dummySimData)).rejects.toThrow(
      'duplicate key value violates unique constraint "settlement_simulations_pkey"'
    );
  });
  test("insertPipelineResults", async () => {
    const txHash = "0x4321";
    const solver = "0xc9ec550bea1c64d779124b23a26292cc223327b6";
    const eventMeta = { txHash: txHash, blockNumber: 0 };
    const settlementEvent = { solver: solver, logIndex: 0 };

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
    const blockNumber = 1;
    const gasUsed = 2;
    const simulationID = "sim-id";
    const largeBigInt = 99999999999999999999999999999999999999999999999999n;
    const exampleLog = {
      address: ethers.ZeroAddress,
      // The indexed topics from the event log
      topics: [ethers.ZeroHash, ethers.ZeroHash],
      data: ethers.ZeroHash,
    };
    const exampleEthDelta = new Map([["0x2", largeBigInt]]);
    const simulationDatum: SettlementSimulationData = {
      txHash,
      full: {
        simulationID,
        gasUsed,
        blockNumber,
        // Note there are 2 logs here!
        logs: [exampleLog, exampleLog],
        ethDelta: exampleEthDelta,
      },
      reduced: {
        simulationID,
        gasUsed,
        blockNumber,
        // and only 1 log here!
        logs: [exampleLog],
        ethDelta: exampleEthDelta,
      },
      winningSettlement: {
        solver: ethers.ZeroAddress,
        simulationBlock: blockNumber,
        reducedCallData: "0xca11da7a",
        fullCallData: "0xca11da7a000000",
      },
    };
    // insertion works.
    await insertPipelineResults(
      db,
      simulationDatum,
      imbalances,
      eventMeta,
      settlementEvent
    );
    const recordCountQuery = sql`select count(*)
                from internalized_imbalances i
                       join settlements s
                            on i.tx_hash = s.tx_hash
                       join settlement_simulations ss
                            on i.tx_hash = ss.tx_hash`;
    let results = await db.query(recordCountQuery);
    expect(results.length).toEqual(1);
    expect(results[0]).toEqual({ count: 2n });

    // Idempotency & insertion works ONLY IF ALL three insertions pass!
    await expect(
      insertPipelineResults(
        db,
        simulationDatum,
        imbalances,
        eventMeta,
        settlementEvent
      )
    ).rejects.toThrow(
      'duplicate key value violates unique constraint "internalized_imbalances_pkey"'
    );
    results = await db.query(recordCountQuery);
    expect(results.length).toEqual(1);
    expect(results[0]).toEqual({ count: 2n });
    await expect(
      insertPipelineResults(db, simulationDatum, [], eventMeta, settlementEvent)
    ).rejects.toThrow(
      'duplicate key value violates unique constraint "settlement_simulations_pkey"'
    );
    results = await db.query(recordCountQuery);
    expect(results.length).toEqual(1);
    expect(results[0]).toEqual({ count: 2n });

    const newTxHash = "0x11";
    eventMeta.txHash = newTxHash;
    simulationDatum.txHash = newTxHash;
    await expect(
      insertPipelineResults(db, simulationDatum, [], eventMeta, settlementEvent)
    ).rejects.toThrow(
      'duplicate key value violates unique constraint "settlements_pkey"'
    );
    results = await db.query(recordCountQuery);
    expect(results.length).toEqual(1);
    expect(results[0]).toEqual({ count: 2n });

    eventMeta.blockNumber += 1; // Different.

    await insertPipelineResults(
      db,
      simulationDatum,
      imbalances,
      eventMeta,
      settlementEvent
    );
    results = await db.query(recordCountQuery);
    expect(results.length).toEqual(1);
    expect(results[0]).toEqual({ count: 4n });
  });
});

describe("jsonFromSettlementData", () => {
  afterAll(async () => {
    await (db as ConnectionPool).dispose();
  });

  test("converts settlement data to database object format", async () => {
    const blockNumber = 1;
    const gasUsed = 2;
    const simulationID = "sim-id";
    const bigNumber = 12345678910999999999999n;
    const dummySimData = {
      simulationID,
      gasUsed,
      blockNumber,
      logs: [
        {
          address: ethers.ZeroAddress,
          // The indexed topics from the event log
          topics: [ethers.ZeroHash],
          data: ethers.ZeroHash,
        },
      ],
      ethDelta: new Map([["0x1", bigNumber]]),
    };
    expect(jsonFromSettlementData(dummySimData)).toStrictEqual({
      blockNumber: 1,
      ethDelta: {
        "0x1": bigNumber.toString(),
      },
      logs: [
        {
          address: ethers.ZeroAddress,
          data: ethers.ZeroHash,
          topics: [ethers.ZeroHash],
        },
      ],
    });
  });
});
