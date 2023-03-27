import { ActionFn, Context, Event, TransactionEvent } from "@tenderly/actions";
import { partitionEventLogs } from "./src/parse";

export const triggerInternalTransfersPipeline: ActionFn = async (
  context: Context,
  event: Event
) => {
  // TODO - https://github.com/cowprotocol/solver-rewards/issues/219
  const transactionEvent = event as TransactionEvent;
  const txHash = transactionEvent.hash;
  console.log(`Received Settlement Event with txHash ${txHash}`);

  const { trades, transfers, settlements } = partitionEventLogs(
    transactionEvent.logs
  );
  if (settlements.length > 1) {
    console.warn(`Two settlements in same batch ${txHash}!`);
    // TODO - alert team that such a batch has taken place!
    //  cf https://github.com/cowprotocol/solver-rewards/issues/187
  }
  console.log(`Parsed ${transfers.length} (relevant) transfer events`);
  console.log(`Parsed ${trades.length} trade events`);
};
