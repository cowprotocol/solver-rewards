import { ActionFn, Context, Event, TransactionEvent } from "@tenderly/actions";
import { txHandler } from "./src/pipeline";

export const triggerInternalTransfersPipeline: ActionFn = async (
  context: Context,
  event: Event
) => {
  // TODO - https://github.com/cowprotocol/solver-rewards/issues/219
  const transactionEvent = event as TransactionEvent;
  const secrets = {
    nodeUrl: await context.secrets.get("NODE_URL"),
    dbUrl: await context.secrets.get("DATABASE_URL"),
    simulatorKey: await context.secrets.get("TENDERLY_ACCESS_KEY"),
  };
  await txHandler(transactionEvent.hash, secrets);
};
