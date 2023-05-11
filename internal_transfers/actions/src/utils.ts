import { EventLog, TransferEvent } from "./models";
import { MinimalTxData } from "./accounting";
import { AbstractProvider } from "ethers";

export function transferInvolves(
  transfer: TransferEvent,
  address: string
): boolean {
  return [transfer.to.toLowerCase(), transfer.from.toLowerCase()].includes(
    address.toLowerCase()
  );
}

export async function getTxDataFromHash(
  provider: AbstractProvider,
  txHash: string
): Promise<MinimalTxData> {
  const transaction = await provider.getTransactionReceipt(txHash);
  if (transaction === null) {
    throw new Error(`invalid transaction hash ${txHash} - try again`);
  }
  const { from, hash, blockNumber, logs: readonlyLogs } = transaction;
  const logs: EventLog[] = readonlyLogs.map(
    ({ index, address, data, topics }) => ({
      index,
      address,
      data,
      topics: [...topics],
    })
  );

  return {
    from,
    hash,
    blockNumber,
    logs,
  };
}
