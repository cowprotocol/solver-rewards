import { EventLog, Trace, TransferEvent } from "./models";
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
      // making a copy of a readonly field!
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

export function ethDeltaFromTraces(traces: Trace[]): Map<string, bigint> {
  const accumulator = new Map<string, bigint>();
  traces.map((trace) => {
    let { to, from, value } = trace;
    const amount = BigInt(value);
    if (amount > 0) {
      to = to.toLowerCase();
      from = from.toLowerCase();
      const currToVal = accumulator.get(to) ?? 0n;
      const currFromVal = accumulator.get(from) ?? 0n;
      accumulator.set(to, currToVal + amount);
      accumulator.set(from, currFromVal - amount);
    }
  });
  return accumulator;
}


export function validateDate(value: string): string {
  if (!/^\d{4}\-(0[1-9]|1[012])\-(0[1-9]|[12][0-9]|3[01])$/.test(value)) {
    throw new Error("Invalid date format. Please use the YYYY-MM-DD format.");
  }
  return value;
}