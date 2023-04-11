import { TokenImbalance } from "./models";
import { ImbalanceMap } from "./utils";

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
