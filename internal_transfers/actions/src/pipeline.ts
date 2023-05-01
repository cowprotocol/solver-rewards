import { partitionEventLogs } from "./parse";
import {
  insertPipelineResults,
  insertSettlementEvent,
  recordExists,
} from "./database";
import {
  getInternalizedImbalance,
  MinimalTxData,
  simulateSolverSolution,
} from "./accounting";
import { Queryable } from "@databases/pg";
import { TransactionSimulator } from "./simulate/interface";

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

  // It's annoying to have to handle the possibility of multiple settlements
  // in the same transaction, but it could happen.
  for (const settlement of settlements) {
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
  }
}
