import { getInternalImbalance, MinimalTxData } from "../src/accounting";
import { TenderlySimulator } from "../src/simulate/tenderly";

describe("getInternalImbalance(transaction, simulator)", () => {
  // TODO - proper e2e test.
  test("throws when no competition found", async () => {
    const invalidSimulator = new TenderlySimulator(
      "INVALID_USER",
      "INVALID_PROJECT",
      "INVALID_KEY"
    );
    const invalidTransaction: MinimalTxData = {
      from: "0x",
      hash: "0x",
      logs: [],
      // Could also use a valid txHash (i.e. the very first batch ever solved on latest settlement contract
      // from: "0x6c2999b6b1fad608ecea71b926d68ee6c62beef8",
      // hash: "0x08100e7ba81be84ee0bdce43db6640e2f992ec9991a740a689e97d20dea9dafa",
    };
    await expect(
      getInternalImbalance(invalidTransaction, invalidSimulator)
    ).rejects.toThrow("No competition found for 0x");
  });
  test("returns early without simulation when fullCallData is undefined", async () => {
    const invalidSimulator = new TenderlySimulator(
      "INVALID_USER",
      "INVALID_PROJECT",
      "INVALID_KEY"
    );
    const uninternalizedSettlement: MinimalTxData = {
      from: "0xb20b86c4e6deeb432a22d773a221898bbbd03036",
      hash: "0xf1df7c1d068c2e0f0cf324bb0739a838fff89b4b08bf2aa11a7b4a609a7e20fe",
      logs: [],
    };
    const result = await getInternalImbalance(
      uninternalizedSettlement,
      invalidSimulator
    );
    expect(result).toEqual([]);
  });
});
