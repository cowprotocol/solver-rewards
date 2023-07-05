import { internalizedTokenImbalance } from "../../src/pipeline";
import { getDB } from "../../src/database";
import { getSampleSet } from "../../src/dune";
import { DuneClient } from "@cowprotocol/ts-dune-client";
import { ethers } from "ethers";
import { TransactionSimulator } from "../../src/simulate/interface";

export async function backFillTokenImbalances(
  dateFrom: string,
  dateTo: string,
  dbUrl: string,
  nodeUrl: string,
  duneApiKey: string,
  simulator: TransactionSimulator
) {
  const dune = new DuneClient(duneApiKey);
  const db = getDB(dbUrl);
  const provider = ethers.getDefaultProvider(nodeUrl);

  const batchDataForDate = await getSampleSet(dune, dateFrom, dateTo);
  console.log(
    `Recovered ${batchDataForDate.length} records for ${dateFrom} ${dateTo}`
  );
  for (const tx of batchDataForDate) {
    try {
      await internalizedTokenImbalance(tx, db, simulator, provider);
    } catch (error: any) {
      // Can't process 0x841ecfc5846f2d5b75f717fa460c81276feabc6140fa8081344c1f3c4178a8c7
      // https://cowservices.slack.com/archives/C0375NV72SC/p1684863431797069
      console.error(error.message);
    }
  }
}
