import {
  bigIntMapToJSON,
  getDB,
  hexToBytea,
  insertSettlementEvent,
  insertSettlementSimulations,
  insertTokenImbalances,
  jsonFromSettlementData,
  insertPipelineResults,
  recordExists,
  insertTxReceipt,
  getUnprocessedReceipts,
  markReceiptProcessed,
  insertSettlementAndMarkProcessed,
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
async function truncateTables() {
  await db.query(sql`TRUNCATE TABLE settlements;`);
  await db.query(sql`TRUNCATE TABLE internalized_imbalances;`);
  await db.query(sql`TRUNCATE TABLE settlement_simulations;`);
  await db.query(sql`TRUNCATE TABLE tx_receipts;`);
}

const largeBigInt =
  115792089237316195423570985008687907853269984665640564039457584007913129639935n;
const tinyBigInt = 1n;
describe("All Database Tests", () => {
  beforeEach(async () => {
    await truncateTables();
  });

  afterAll(async () => {
    await (db as ConnectionPool).dispose();
  });

  describe("test database methods", () => {
    test("insertSettlementEvent(txHash, solver) succeeds and fails second attempt", async () => {
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
    test("insertImbalances(txHash, imbalances) succeeds and fails second attempt", async () => {
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

      await expect(
        insertTokenImbalances(db, txHash, imbalances)
      ).rejects.toThrow(
        'duplicate key value violates unique constraint "internalized_imbalances_pkey"'
      );
    });
    test("insertSimulations(datum) works and fails second attempt", async () => {
      const blockNumber = 1;
      const gasUsed = 2;
      const simulationID = "sim-id";
      const largeBigInt = 99999999999999999999999999999999999999999999999999n;
      const exampleLog = {
        index: 0,
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

      let results = await db.query(sql`SELECT * from settlement_simulations;`);
      const expected = [
        {
          complete: {
            simId: "sim-id",
            gasUsed: 2,
            blockNumber: blockNumber,
            ethDelta: bigIntMapToJSON(exampleEthDelta),
            logs: [exampleLog, exampleLog],
          },
          reduced: {
            simId: "sim-id",
            gasUsed: 2,
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

      await expect(
        insertSettlementSimulations(db, dummySimData)
      ).rejects.toThrow(
        'duplicate key value violates unique constraint "settlement_simulations_pkey"'
      );
    });
    test("recordExists(txHash) accurately performs its job", async () => {
      const txHash =
        "0x45f52ee09622eac16d0fe27b90a76749019b599c9566f10e21e8d0955a0e428e";

      expect(await recordExists(db, txHash)).toEqual(false);
      await insertSettlementEvent(
        db,
        { txHash: txHash, blockNumber: 0 },
        { solver: "0xc9ec550bea1c64d779124b23a26292cc223327b6", logIndex: 0 }
      );
      expect(await recordExists(db, txHash)).toEqual(true);
    });
    test("insertTxReceipt(receipt)", async () => {
      const hash = "0x";
      const receipt = {
        logs: [],
        blockNumber: 1,
        hash,
        from: "0x",
      };
      await insertTxReceipt(db, receipt);
      let results = await db.query(sql`SELECT * from tx_receipts;`);
      expect(results).toEqual([
        {
          block_number: 1n,
          data: receipt,
          hash: hexToBytea(hash),
          processed: false,
        },
      ]);
    });
    test("getUnprocessedReceipts(blockFrom)", async () => {
      const hashes = ["0x01", "0x02"];
      const receipts = hashes.map((value, index) => {
        return {
          logs: [],
          blockNumber: index,
          hash: value,
          from: "0x",
        };
      });
      await insertTxReceipt(db, receipts[0]);
      await insertTxReceipt(db, receipts[1]);
      const emptyResults = await getUnprocessedReceipts(db, 0);
      expect(emptyResults).toEqual([]);
      const oneResult = await getUnprocessedReceipts(db, 1);
      expect(oneResult).toEqual([receipts[0]]);
      const twoResults = await getUnprocessedReceipts(db, 2);
      expect(twoResults).toEqual(receipts);
    });
    test("markReceiptProcessed works when exists", async () => {
      const receipt = {
        logs: [],
        blockNumber: 0,
        hash: "0x01",
        from: "0x",
      };
      await insertTxReceipt(db, receipt);
      await markReceiptProcessed(db, receipt.hash);
      let results = await db.query(sql`SELECT * from tx_receipts;`);
      expect(results).toEqual([
        {
          block_number: 0n,
          data: receipt,
          hash: hexToBytea(receipt.hash),
          processed: true,
        },
      ]);
    });
    test("markReceiptProcessed does nothing when hash doesn't exist", async () => {
      await expect(
        markReceiptProcessed(db, "0x01")
      ).resolves.not.toThrowError();
    });

    test("insertSettlementAndMarkProcessed works together", async () => {
      const hash = "0x";
      const solver = "0x50";
      const receipt = {
        logs: [],
        blockNumber: 1,
        hash,
        from: solver,
      };
      await insertTxReceipt(db, receipt);
      await insertSettlementAndMarkProcessed(
        db,
        { txHash: hash, blockNumber: 0 },
        { solver: solver, logIndex: 0 }
      );

      expect(await db.query(sql`SELECT * from tx_receipts;`)).toEqual([
        {
          block_number: 1n,
          data: {
            blockNumber: 1,
            from: "0x50",
            hash: "0x",
            logs: [],
          },
          hash: hexToBytea(hash),
          // This is the key point (processed = true)
          processed: true,
        },
      ]);
      expect(await db.query(sql`SELECT * from settlements;`)).toStrictEqual([
        {
          block_number: 0n,
          log_index: 0n,
          solver: hexToBytea(solver),
          tx_hash: hexToBytea(hash),
        },
      ]);
    });
  });

  describe("insertPipelineResults", () => {
    beforeEach(async () => {
      await truncateTables();
    });

    function getTestData() {
      const txHash = "0x4321";
      const solver = "0xc9ec550bea1c64d779124b23a26292cc223327b6";
      const token1 = "0x12";
      const token2 = "0x34";
      const simulationBlock = 1;
      const exampleLog = {
        index: 0,
        address: ethers.ZeroAddress,
        // The indexed topics from the event log
        topics: [ethers.ZeroHash, ethers.ZeroHash],
        data: ethers.ZeroHash,
      };
      const exampleEthDelta = new Map([["0x2", largeBigInt]]);
      const simulationCommon = {
        simulationID: "whatever-string",
        gasUsed: 2,
        blockNumber: simulationBlock,
        ethDelta: exampleEthDelta,
      };
      return {
        eventMeta: { txHash: txHash, blockNumber: 0 },
        settlementSimulations: {
          txHash,
          full: {
            ...simulationCommon,
            // Note there are 2 logs here!
            logs: [exampleLog, exampleLog],
          },
          reduced: {
            ...simulationCommon,
            // and only 1 log here!
            logs: [exampleLog],
          },
          winningSettlement: {
            solver: ethers.ZeroAddress,
            simulationBlock,
            reducedCallData: "0xca11da7a",
            fullCallData: "0xca11da7a000000",
          },
        },
        settlementEvent: { solver: solver, logIndex: 0 },
        imbalances: [
          { token: token1, amount: largeBigInt },
          { token: token2, amount: tinyBigInt },
        ],
      };
    }

    test("insertion works and fails second attempt", async () => {
      // insertion works.
      const testResults = getTestData();
      await insertPipelineResults(db, testResults);
      const recordCountQuery = sql`select count(*)
                                 from internalized_imbalances i
                                        join settlements s
                                             on i.tx_hash = s.tx_hash
                                        join settlement_simulations ss
                                             on i.tx_hash = ss.tx_hash`;
      let results = await db.query(recordCountQuery);
      expect(results.length).toEqual(1);
      expect(results[0]).toEqual({ count: 2n });

      // insertion works ONLY IF ALL three insertions pass!
      await expect(insertPipelineResults(db, testResults)).rejects.toThrow(
        'duplicate key value violates unique constraint "internalized_imbalances_pkey"'
      );
    });
    test("insertion fails if only imbalances differs", async () => {
      let testResults = getTestData();
      await insertPipelineResults(db, testResults);
      testResults.imbalances = [];
      await expect(insertPipelineResults(db, testResults)).rejects.toThrow(
        'duplicate key value violates unique constraint "settlement_simulations_pkey"'
      );
    });
    test("insertion fails if imbalances is settlement Event is same", async () => {
      let testResults = getTestData();
      await insertPipelineResults(db, testResults);
      testResults.imbalances = [];
      const newTxHash = "0x11";
      testResults.eventMeta.txHash = newTxHash;
      testResults.settlementSimulations.txHash = newTxHash;
      await expect(insertPipelineResults(db, testResults)).rejects.toThrow(
        'duplicate key value violates unique constraint "settlements_pkey"'
      );
    });

    test("insertion works again if all three insertions pass", async () => {
      let testResults = getTestData();
      await insertPipelineResults(db, testResults);

      // Changing sufficient information so that all three insertions succeed
      testResults.imbalances = [];
      const newTxHash = "0x11";
      testResults.eventMeta.txHash = newTxHash;
      testResults.settlementSimulations.txHash = newTxHash;
      testResults.eventMeta.blockNumber += 1; // Different Block Number ==> different Settlement Event
      await insertPipelineResults(db, testResults);
    });
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
          index: 0,
          address: ethers.ZeroAddress,
          // The indexed topics from the event log
          topics: [ethers.ZeroHash],
          data: ethers.ZeroHash,
        },
      ],
      ethDelta: new Map([["0x1", bigNumber]]),
    };
    expect(jsonFromSettlementData(dummySimData)).toStrictEqual({
      simId: simulationID,
      gasUsed,
      blockNumber: 1,
      ethDelta: {
        "0x1": bigNumber.toString(),
      },
      logs: [
        {
          index: 0,
          address: ethers.ZeroAddress,
          data: ethers.ZeroHash,
          topics: [ethers.ZeroHash],
        },
      ],
    });
  });
});
