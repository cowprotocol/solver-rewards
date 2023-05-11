import { ActionFn, Context, Event, TransactionEvent } from "@tenderly/actions";
import { getDB } from "./src/database";
import { ethers } from "ethers";
import {
  internalizedTokenImbalance,
  preliminaryPipelineTask,
} from "./src/pipeline";
import { TenderlySimulator } from "./src/simulate/tenderly";

export const triggerInternalTransfersPipeline: ActionFn = async (
  context: Context,
  event: Event
) => {
  // TODO - https://github.com/cowprotocol/solver-rewards/issues/219
  const transactionEvent = event as TransactionEvent;

  const txHash = transactionEvent.hash;
  console.log(`Received Settlement Transaction with hash ${txHash}`);
  const provider = ethers.getDefaultProvider(
    await context.secrets.get("NODE_URL")
  );
  const db = getDB(await context.secrets.get("DATABASE_URL"));

  const finalizedTxReceipts = await preliminaryPipelineTask(
    db,
    provider,
    txHash
  );
  console.log("Inserted to backlog")
  const simulator = new TenderlySimulator(
    "gp-v2",
    "solver-slippage",
    await context.secrets.get("TENDERLY_ACCESS_KEY")
  );
  for (const tx of finalizedTxReceipts) {
    // Theoretically, there are only be 1 or 2 of these to process in a single run.
    await internalizedTokenImbalance(tx, db, simulator);
  }
};
