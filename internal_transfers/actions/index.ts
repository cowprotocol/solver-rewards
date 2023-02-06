import {
	ActionFn,
	Context,
	Event,
	TransactionEvent,
} from '@tenderly/actions';

export const triggerInternalTransfersPipeline: ActionFn = async (
  context: Context,
  event: Event
) => {
	const transactionEvent = event as TransactionEvent;
 	const txHash = transactionEvent.hash;
     console.log(`Received Settlement Event with txHash ${txHash}`);
};
