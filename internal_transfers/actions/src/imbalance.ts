import { TokenImbalance, TransferEvent } from "./models";

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
  const accumulator: ImbalanceMap = new Map<string, bigint>();
  transfers.map((transfer) => {
    let { to, from, amount, token } = transfer;
    token = token.toLowerCase();
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

/**
 * Difference operator on two token imbalance mappings.
 * More generally, this computes the difference of two mappings of type { string => bigint }.
 * Example: ({ "a": 1, "b": 2 }, { "b": 3, "c": 4 }) --> { "a": 1, "b": -1, "c": -4 }
 * @param mapA positive term - being subtracted from
 * @param mapB negative term - being subtracted
 * @return mapA - mapB as a list of TokenImbalance
 */
export function imbalanceMapDiff(
  mapA: ImbalanceMap,
  mapB: ImbalanceMap
): TokenImbalance[] {
  const keySet = new Set([...mapA.keys(), ...mapB.keys()]);
  let diffMap: ImbalanceMap = new Map<string, bigint>();
  for (const token of keySet) {
    const difference = (mapA.get(token) ?? 0n) - (mapB.get(token) ?? 0n);
    if (difference !== 0n) {
      // No point in recording zeros!
      diffMap.set(token, difference);
    }
  }
  return Array.from(diffMap).map(([token, amount]) => ({
    token,
    amount,
  }));
}
