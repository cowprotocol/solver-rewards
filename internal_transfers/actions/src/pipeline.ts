import { partitionEventLogs } from "./parse";
import {
  getUnprocessedReceipts,
  insertPipelineResults,
  insertSettlementAndMarkProcessed,
  insertTxReceipt,
  recordExists,
} from "./database";
import {
  getInternalizedImbalance,
  MinimalTxData,
  SettlementSimulationData,
  simulateSolverSolution,
} from "./accounting";
import { Queryable } from "@databases/pg";
import { TransactionSimulator } from "./simulate/interface";
import { AbstractProvider } from "ethers";
import { getTxDataFromHash } from "./utils";

/** Consumes a transaction hash, fetches corresponding transaction receipt,
 * writes the receipt to a database, then fetches and returns all previously
 * unprocessed, but ready, transaction receipts.
 *
 * @param db - Connection to a database
 * @param provider - Ethereum network provider
 * @param txHash - Ethereum Transaction Hash
 * @param numConfirmationBlocks transaction finalization block confirmations
 * @return an array of "finalized" Transaction Receipts
 */
export async function preliminaryPipelineTask(
  db: Queryable,
  provider: AbstractProvider,
  txHash: string,
  // Services uses 64 blocks as assumed finalization, we must use at least this many to assume data availability:
  // cf - https://github.com/cowprotocol/services/blob/042aac25dbb2219b4498142738cb87e3ddca7b45/crates/shared/src/event_handling.rs#L21
  numConfirmationBlocks: number = 70
): Promise<MinimalTxData[]> {
  const txReceipt = await getTxDataFromHash(provider, txHash);
  const { trades } = partitionEventLogs(txReceipt.logs);
  if (trades.length > 0) {
    await insertTxReceipt(db, txReceipt);
  } else {
    // E.g. Fee Withdrawal:
    // https://etherscan.io/tx/0x72971bf0203c472c58ba0970c9cd99c14c153badac787186f3856b416a6ff59c
    console.log("No trades in batch");
  }

  return getUnprocessedReceipts(
    db,
    txReceipt.blockNumber - numConfirmationBlocks
  );
}

/**
 *  Consumes a data for an ethereum transaction (pertaining to a Settlement Event),
 *  parses relevant event logs,
 *  fetches winning solver competition,
 *  simulates winning settlement data,
 *  computes internalized token imbalance and
 *  writes results to database.
 *
 * @param txData -- Relevant transaction data from transaction receipt
 * @param db -- Connection to a database
 * @param simulator -- Instance of a TransactionSimulator
 * @param provider -- web3 Provider (for making ETH calls)
 */
export async function internalizedTokenImbalance(
  txData: MinimalTxData,
  db: Queryable,
  simulator: TransactionSimulator,
  provider: AbstractProvider
): Promise<void> {
  const txHash = txData.hash;
  console.log(`processing settlement transaction with hash: ${txData.hash}`);
  // Duplication Guard!
  if (await recordExists(db, txHash)) {
    console.warn(`event record exists for tx: ${txHash}`);
    return;
  }

  // There are other events being returned here, but we only need the settlement(s)
  const { settlements } = partitionEventLogs(txData.logs);

  // It's annoying to have to handle the possibility of multiple settlements
  // in the same transaction, but it could happen.
  for (const settlement of settlements) {
    let settlementSimulations: SettlementSimulationData | null;
    try {
      settlementSimulations = await simulateSolverSolution(txData, simulator);
    } catch (error) {
      // Block containing transaction was likely forked and no longer exists.
      // The correct approach here is to validate this by re-fetching
      // the transaction receipt and validating that logs = []
      const reFetchedReceipt = await getTxDataFromHash(provider, txHash);
      if (reFetchedReceipt.logs.length === 0) {
        settlementSimulations = null;
      } else {
        throw error;
      }
    }
    const eventMeta = { txHash, blockNumber: txData.blockNumber };
    const settlementEvent = settlement;
    // If there is a simulation, get imbalances otherwise assume none.
    if (settlementSimulations) {
      await insertPipelineResults(db, {
        settlementSimulations,
        imbalances: getInternalizedImbalance(settlementSimulations),
        eventMeta,
        settlementEvent,
      });
    } else {
      await insertSettlementAndMarkProcessed(db, eventMeta, settlementEvent);
    }
  }
}
