import {
  constructImbalanceMap,
  getInternalizedImbalance,
  MinimalTxData,
  SettlementSimulationData,
  simulateSolverSolution,
} from "../src/accounting";
import { TenderlySimulator } from "../src/simulate/tenderly";

describe("getInternalizedImbalance(simulationData)", () => {
  test("does the thing", async () => {
    const blockNumber = 1;
    const dummySimData: SettlementSimulationData = {
      txHash: "0x1",
      full: { blockNumber, logs: [], ethDelta: new Map([["0x", 1n]]) },
      reduced: { blockNumber, logs: [], ethDelta: new Map([["0x", 1n]]) },
      winningSettlement: {
        solver: "0x",
        simulationBlock: 1,
        reducedCallData: "0x",
        fullCallData: "0x",
      },
    };
    expect(getInternalizedImbalance(dummySimData)).toStrictEqual([]);
  });
});
describe("simulateSolverSolution(transaction, simulator)", () => {
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
      simulateSolverSolution(invalidTransaction, invalidSimulator)
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
    const result = await simulateSolverSolution(
      uninternalizedSettlement,
      invalidSimulator
    );
    expect(result).toEqual(null);
  });
});

describe("constructImbalanceMap(simulation, focalContract)", () => {
  test("constructs imbalances as expected with ETH Delta", async () => {
    const simulationWithETH = {
      blockNumber: 16530828,
      txHash:
        "0x0e50d5447266171a4daf32880dfef3f55e31b7b80b285d14ddaefa6ad8098221",
      logs: [
        {
          address: "0xa0b86991c6218b36c1d19d4a2e9eb0ce3606eb48",
          topics: [
            "0xddf252ad1be2c89b69c2b068fc378daa952ba7f163c4a11628f55a4df523b3ef",
            "0x0000000000000000000000005c10c47b2d848e06a5dffa45b3bc10860797cdad",
            "0x0000000000000000000000009008d19f58aabd9ed0d60971565aa8510560ab41",
          ],
          data: "0x000000000000000000000000000000000000000000000000000000000000000f", // +15
        },
        {
          address: "0xa0b86991c6218b36c1d19d4a2e9eb0ce3606eb48",
          topics: [
            "0xddf252ad1be2c89b69c2b068fc378daa952ba7f163c4a11628f55a4df523b3ef",
            "0x0000000000000000000000009008d19f58aabd9ed0d60971565aa8510560ab41",
            "0x0000000000000000000000005c10c47b2d848e06a5dffa45b3bc10860797cdad",
          ],
          data: "0x00000000000000000000000000000000000000000000000000000000000000ff", // -255
        },
      ],
      ethDelta: new Map([
        ["0x9008d19f58aabd9ed0d60971565aa8510560ab41", 12345n],
        ["0xIrrelevantAccount", 1n],
      ]),
    };
    await expect(
      constructImbalanceMap(
        simulationWithETH,
        "0x9008d19f58aabd9ed0d60971565aa8510560ab41"
      )
    ).toEqual(
      new Map([
        ["0xa0b86991c6218b36c1d19d4a2e9eb0ce3606eb48", -240n],
        ["0xeeeeeeeeeeeeeeeeeeeeeeeeeeeeeeeeeeeeeeee", 12345n],
      ])
    );
  });

  test("constructs imbalances as expected without ETH Delta", async () => {
    const simulationNoEth = {
      blockNumber: 16530828,
      txHash: "0x",
      logs: [
        {
          address: "0xtoken",
          topics: [
            "0xddf252ad1be2c89b69c2b068fc378daa952ba7f163c4a11628f55a4df523b3ef",
            "0x0000000000000000000000005c10c47b2d848e06a5dffa45b3bc10860797cdad",
            "0x0000000000000000000000009008d19f58aabd9ed0d60971565aa8510560ab41",
          ],
          data: "0x000000000000000000000000000000000000000000000000000000000000000f", // 15n
        },
      ],
      ethDelta: new Map([
        ["0x9008d19f58aabd9ed0d60971565aa8510560ab41", 0n],
        ["0xIrrelevantAccount", 1n],
      ]),
    };
    await expect(
      constructImbalanceMap(
        simulationNoEth,
        "0x9008d19f58aabd9ed0d60971565aa8510560ab41"
      )
    ).toEqual(new Map([["0xtoken", 15n]]));
  });
});
