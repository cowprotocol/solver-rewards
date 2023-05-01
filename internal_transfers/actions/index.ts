import { ActionFn, Context, Event, TransactionEvent } from "@tenderly/actions";
import { getDB } from "./src/database";
import { TenderlySimulator } from "./src/simulate/tenderly";
import { internalizedTokenImbalance } from "./src/pipeline";

export const triggerInternalTransfersPipeline: ActionFn = async (
  context: Context,
  event: Event
) => {
  // TODO - https://github.com/cowprotocol/solver-rewards/issues/219
  const transactionEvent = event as TransactionEvent;
  const db = getDB(await context.secrets.get("DATABASE_URL"));
  const simulator = new TenderlySimulator(
    await context.secrets.get("TENDERLY_USER"),
    await context.secrets.get("TENDERLY_PROJECT"),
    await context.secrets.get("TENDERLY_ACCESS_KEY")
  );
  await internalizedTokenImbalance(transactionEvent, db, simulator);
};
