import { internalizedTokenImbalance } from "../../src/pipeline";
import { getDB } from "../../src/database";
import { getSampleSet } from "../../src/dune";
import { DuneClient } from "@cowprotocol/ts-dune-client";
import { ethers } from "ethers";
import { TransactionSimulator } from "../../src/simulate/interface";

export async function backFillTokenImbalances(
  dateStr: string,
  simulator: TransactionSimulator
) {
  const { DUNE_API_KEY, DB_URL, NODE_URL } = process.env;
  const dune = new DuneClient(DUNE_API_KEY!);
  const db = getDB(DB_URL!);
  const provider = ethers.getDefaultProvider(NODE_URL!);

  const batchDataForDate = await getSampleSet(dune, dateStr);
  console.log(`Recovered ${batchDataForDate.length} records for ${dateStr}`);
  for (const tx of batchDataForDate) {
    await internalizedTokenImbalance(tx, db, simulator, provider);
  }
}
