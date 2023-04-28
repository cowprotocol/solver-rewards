import { TransferEvent } from "./models";
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
  const logs = readonlyLogs.map((log) => {
    return {
      ...log,
      // had to Map it to make a copy of a readonly field.
      topics: log.topics.map((value) => value),
    };
  });

  return {
    from,
    hash,
    blockNumber,
    logs,
  };
}
