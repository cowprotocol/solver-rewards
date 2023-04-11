import { TransferEvent } from "./models";

export type ImbalanceMap = Map<string, bigint>;

/**
 * Aggregation operator transforming a list of `TransferEvent` into an
 * aggregation of token imbalances as an `ImbalanceMap`.
 * Imbalances are defined in reference to `focalAccount`
 * @param transfers - a list of token transfers
 * @param focalAccount - account for which the "imbalance" is referring to.
 */
export function aggregateTransfers(
  transfers: TransferEvent[],
  focalAccount: string
): ImbalanceMap {
  let accumulator: ImbalanceMap = new Map<string, bigint>();
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
  return accumulator;
}

export function transferInvolves(
  transfer: TransferEvent,
  address: string
): boolean {
  return [transfer.to.toLowerCase(), transfer.from.toLowerCase()].includes(
    address.toLowerCase()
  );
}
