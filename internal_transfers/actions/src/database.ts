// Code Reference: https://www.atdatabases.org/docs/pg-guide-typescript

import createConnectionPool, { sql } from "@databases/pg";
import tables from "@databases/pg-typed";
import ConnectionPool from "@databases/pg/lib/types/Queryable";
import DatabaseSchema from "./__generated__";
import { EventMeta, SettlementEvent } from "./models";

export { sql };
const { settlements } = tables<DatabaseSchema>({
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
  console.log("inserted settlement event to DB");
}

function hexToBytea(hexString: string): Buffer {
  return Buffer.from(hexString.slice(2), "hex");
}

export { settlements, insertSettlementEvent, getDB, hexToBytea };
