import { MinimalTxData } from "../../src/accounting";
import { ethers } from "ethers";
import { getTxDataFromHash } from "../../src/utils";

export async function getTxData(txHash: string): Promise<MinimalTxData> {
  const provider = ethers.getDefaultProvider(
    process.env["NODE_URL"] || "NODE_URL"
  );
  return getTxDataFromHash(provider, txHash);
}
