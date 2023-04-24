// Code Reference: https://www.atdatabases.org/docs/pg-guide-typescript

import createConnectionPool, { sql } from "@databases/pg";
import tables from "@databases/pg-typed";
import ConnectionPool from "@databases/pg/lib/types/Queryable";
import DatabaseSchema from "./__generated__";
import { EventMeta, SettlementEvent, TokenImbalance } from "./models";
import { SettlementSimulationData } from "./accounting";
import { SimulationData } from "./simulate/interface";
// import { IsolationLevel } from "@databases/pg";

export { sql };
const { settlements, internalized_imbalances, settlement_simulations } =
  tables<DatabaseSchema>({
    databaseSchema: require("./__generated__/schema.json"),
  });

function getDB(dbURL: string): ConnectionPool {
  return createConnectionPool({
    connectionString: dbURL,
    bigIntMode: "bigint",
  });
}
async function insertSettlementEvent(
  db: ConnectionPool,
  eventMeta: EventMeta,
  settlementEvent: SettlementEvent
) {
  const { solver, logIndex } = settlementEvent;
  const { txHash, blockNumber } = eventMeta;
  await settlements(db).insert({
    tx_hash: hexToBytea(txHash),
    solver: hexToBytea(solver),
    block_number: blockNumber,
    log_index: logIndex,
  });
}

async function insertTokenImbalances(
  db: ConnectionPool,
  txHash: string,
  imbalances: TokenImbalance[]
) {
  await internalized_imbalances(db).bulkInsert({
    columnsToInsert: ["token", "tx_hash", "amount"],
    records: imbalances.map((imbalance) => {
      return {
        token: hexToBytea(imbalance.token),
        tx_hash: hexToBytea(txHash),
        amount: imbalance.amount.toString(),
      };
    }),
  });
}

export function bigIntMapToJSON(originalMap: Map<string, bigint>): object {
  return Object.fromEntries(
    new Map(Array.from(originalMap, ([k, v]) => [k, v.toString()]))
  );
}
export function jsonFromSettlementData(datum: SimulationData): object {
  return {
    logs: datum.logs,
    blockNumber: datum.blockNumber,
    ethDelta: bigIntMapToJSON(datum.ethDelta),
  };
}

async function insertSettlementSimulations(
  db: ConnectionPool,
  datum: SettlementSimulationData
) {
  await settlement_simulations(db).insert({
    tx_hash: hexToBytea(datum.txHash),
    complete: jsonFromSettlementData(datum.full),
    reduced: jsonFromSettlementData(datum.reduced),
    winning_settlement: datum.winningSettlement,
  });
}
export async function insertPipelineResults(
  db: ConnectionPool,
  simulationDatum: SettlementSimulationData,
  imbalances: TokenImbalance[],
  eventMeta: EventMeta,
  settlementEvent: SettlementEvent
) {
  await db.tx(
    async (db) => {
      await insertTokenImbalances(db, eventMeta.txHash, imbalances);
      await insertSettlementSimulations(db, simulationDatum);
      await insertSettlementEvent(db, eventMeta, settlementEvent);
    }
    // {
    //   isolationLevel: IsolationLevel.SERIALIZABLE,
    //   retrySerializationFailures: true,
    // }
  );
}

function hexToBytea(hexString: string): Buffer {
  return Buffer.from(hexString.slice(2), "hex");
}

export {
  insertSettlementEvent,
  insertTokenImbalances,
  getDB,
  hexToBytea,
  insertSettlementSimulations,
};
