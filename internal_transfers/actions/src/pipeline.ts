import { partitionEventLogs } from "./parse";
import { insertPipelineResults, insertSettlementEvent } from "./database";
import {
  getInternalizedImbalance,
  MinimalTxData,
  simulateSolverSolution,
} from "./accounting";
import { Queryable, sql } from "@databases/pg";
import { TransactionSimulator } from "./simulate/interface";

async function recordExists(db: Queryable, txHash: string): Promise<boolean> {
  const pgHash = txHash.replace("0x", "\\x");
  const query = sql`SELECT count(*) from settlements where tx_hash = ${pgHash};`;
  const { count: numRecords } = (await db.query(query))[0];
  return numRecords > 0;
}

export async function internalizedTokenImbalance(
  txData: MinimalTxData,
  db: Queryable,
  simulator: TransactionSimulator
): Promise<void> {
  const txHash = txData.hash;
  console.log(`processing settlement transaction with hash: ${txData.hash}`);
  // Duplication Guard!
  if (await recordExists(db, txHash)) {
    console.warn(`record exists for tx: ${txHash}`);
    return;
  }

  // There are other events being returned here, but we only need the settlement(s)
  const { settlements } = partitionEventLogs(txData.logs);

  if (settlements.length > 1) {
    console.warn(`Two settlements in same batch ${txHash}!`);
    // TODO - alert team that such a batch has taken place!
    //  cf https://github.com/cowprotocol/solver-rewards/issues/187
  }

  // It's annoying to have to handle the possibility of multiple settlements
  // in the same transaction, but it could happen.
  for (const settlement of settlements) {
    try {
      const settlementSimulations = await simulateSolverSolution(
        txData,
        simulator
      );
      const eventMeta = { txHash, blockNumber: txData.blockNumber };
      const settlementEvent = settlement;
      if (settlementSimulations) {
        // If there is a simulation, get imbalances otherwise assume none.
        await insertPipelineResults(db, {
          settlementSimulations,
          imbalances: getInternalizedImbalance(settlementSimulations),
          eventMeta,
          settlementEvent,
        });
      } else {
        await insertSettlementEvent(db, eventMeta, settlementEvent);
      }
    } catch (error) {}
  }
}
