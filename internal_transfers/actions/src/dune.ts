import { QueryParameter, DuneClient } from "@cowprotocol/ts-dune-client";
import { MinimalTxData } from "./accounting";

const TX_DATA_QUERY_ID = 2492342;

export async function getSampleSet(
  dune: DuneClient,
  // YYYY-MM-DD
  dateFrom: string,
  dateTo: string
): Promise<MinimalTxData[]> {
  const historicalTransactionData = await dune
    .refresh(TX_DATA_QUERY_ID, [
      QueryParameter.date("DateFrom", `${dateFrom} 00:00:00`),
      QueryParameter.date("DateTo", `${dateTo} 00:00:00`),
    ])
    .then((executionResult) => executionResult.result);
  if (!historicalTransactionData) {
    throw new Error("Failure");
  }

  return historicalTransactionData!.rows.map((row: Record<string, any>) => {
    const { blockNumber, from, hash, logs } = row;
    if (!isEventLogArray(logs)) {
      throw Error(`Invalid Row ${JSON.stringify(row)}`);
    }
    return {
      blockNumber: parseInt(blockNumber),
      from,
      hash,
      logs: logs.map((log) => JSON.parse(log)),
    };
  });
}

function isEventLogArray(value: any): value is Array<string> {
  return value instanceof Array;
}
