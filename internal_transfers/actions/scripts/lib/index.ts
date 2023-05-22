import { internalizedTokenImbalance } from "../../src/pipeline";
import { getDB } from "../../src/database";
import { getSampleSet } from "../../src/dune";
import { DuneClient } from "@cowprotocol/ts-dune-client";
import { ethers } from "ethers";
import { TransactionSimulator } from "../../src/simulate/interface";

export async function backFillTokenImbalances(
  dateStr: string,
  dbUrl: string,
  nodeUrl: string,
  duneApiKey: string,
  simulator: TransactionSimulator
) {
  const dune = new DuneClient(duneApiKey);
  const db = getDB(dbUrl);
  const provider = ethers.getDefaultProvider(nodeUrl);

  const batchDataForDate = await getSampleSet(dune, dateStr);
  console.log(`Recovered ${batchDataForDate.length} records for ${dateStr}`);
  for (const tx of batchDataForDate) {
    await internalizedTokenImbalance(tx, db, simulator, provider);
  }
}
