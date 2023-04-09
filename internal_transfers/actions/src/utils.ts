import { TokenImbalance, TransferEvent } from "./models";

export function aggregateTransfers(
  transfers: TransferEvent[],
  focalAccount: string
): TokenImbalance[] {
  let accumulator = new Map<string, bigint>();
  transfers.map((transfer) => {
    const { to, from, amount, token } = transfer;

    const currVal = accumulator.get(token) ?? 0n;
    if (to.toLowerCase() == focalAccount.toLowerCase()) {
      // Incoming Transfer
      accumulator.set(token, currVal + amount);
    } else if (from.toLowerCase() == focalAccount.toLowerCase()) {
      // Outgoing Transfer
      accumulator.set(token, currVal - amount);
    } else {
      // Irrelevant transfer.
    }
  });
  return Array.from(accumulator).map(([token, amount]) => ({
    token,
    amount,
  }));
}

export function transferInvolves(
  transfer: TransferEvent,
  address: string
): boolean {
  return [transfer.to.toLowerCase(), transfer.from.toLowerCase()].includes(
    address.toLowerCase()
  );
}
