import { ActionFn, Context, Event, TransactionEvent } from "@tenderly/actions";
import { partitionEventLogs } from "./src/parse";

export const triggerInternalTransfersPipeline: ActionFn = async (
  context: Context,
  event: Event
) => {
  const transactionEvent = event as TransactionEvent;
  const txHash = transactionEvent.hash;
  console.log(`Received Settlement Event with txHash ${txHash}`);

  const { trades, transfers, settlements } = partitionEventLogs(
    transactionEvent.logs
  );
  if (settlements.length > 1) {
    console.error(`Two settlements in same batch ${txHash}!`);
  }

  console.log(`Parsed ${transfers.length} (relevant) transfer events`);
  console.log(`Parsed ${trades.length} trade events`);
};
