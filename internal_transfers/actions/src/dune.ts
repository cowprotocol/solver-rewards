import { QueryParameter, DuneClient } from "@cowprotocol/ts-dune-client";
import { MinimalTxData } from "./accounting";

export async function getSampleSet(
  dune: DuneClient,
  // YYYY-MM-DD
  dateStr: string
): Promise<MinimalTxData[]> {
  const historicalTransactionData = await dune
    // Uncomment this to run for a whole month.
    // Will take a VERY LONG TIME
    // ~ 7 minutes / day with Tenderly ==> (3.5 HOURS)
    // ~ 39 minutes / day with Enso ==> (19 HOURS)
    .refresh(2492342, [QueryParameter.date("Month", `${dateStr} 00:00:00`)])
    // .refresh(2470893, [QueryParameter.date("BlockDate", `${dateStr} 00:00:00`)])
    .then((executionResult) => executionResult.result);
  if (historicalTransactionData === undefined) {
    throw new Error("Failure");
  }

  return historicalTransactionData.rows.map((row: Record<string, any>) => {
    const { blockNumber, from, hash, logs } = row;
    if (!isEventLogArray(logs)) {
      throw Error(`Invalid Row ${JSON.stringify(row)}`);
    }
    return {
      blockNumber: parseInt(blockNumber),
      from: from,
      hash: hash,
      logs: logs.map((log) => JSON.parse(log)),
    };
  });
}

function isEventLogArray(value: any): value is Array<string> {
  return value instanceof Array;
}
