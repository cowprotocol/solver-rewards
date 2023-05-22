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

//   // Capped Parallel Processing:
//   const cap = 5;
//   const skipLog = [
//       "0x755fee04e6c2a09f3c356f5b192a00830894e42008725ae1f0119fe1a7c44f97" // January 3
//   ]
//   for (const part of partition(batchDataForDate, cap)) {
//     await Promise.all(
//       part.map((tx) => {
//         if (!skipLog.includes(tx.hash)) {
//           internalizedTokenImbalance(tx, db, simulator, provider, true);
//         }
//       })
//     );
//     console.log("nap time;")
//     await sleep(2);
//   }
// function partition(array: MinimalTxData[], size: number): MinimalTxData[][] {
//   return array.length
//     ? [array.splice(0, size)].concat(partition(array, size))
//     : [];
// }
