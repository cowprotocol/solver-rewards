import {
  getInternalizedImbalance,
  simulateSolverSolution,
} from "../../src/accounting";
import { TenderlySimulator } from "../../src/simulate/tenderly";
import { getTxData } from "./helper";

const simulator = new TenderlySimulator(
  process.env["TENDERLY_USER"] || "INVALID_USER",
  process.env["TENDERLY_PROJECT"] || "TENDERLY_PROJECT",
  process.env["TENDERLY_ACCESS_KEY"] || "TENDERLY_ACCESS_KEY"
);
describe.skip("simulateSolverSolution(transaction, simulator)", () => {
  test("throws when no competition found", async () => {
    const txHash =
      "0x08100e7ba81be84ee0bdce43db6640e2f992ec9991a740a689e97d20dea9dafa";
    const transaction = await getTxData(txHash);
    await expect(
      simulateSolverSolution(transaction, simulator)
    ).rejects.toThrow(`No competition found for ${txHash}`);
  });
  test("runs as expected on legit txHash with no internalization", async () => {
    const transaction = await getTxData(
      "0x3b2e9675b6d71a34e9b7f4abb4c9e80922be311076fcbb345d7da9d91a05e048"
    );
    const imbalance = await simulateSolverSolution(transaction, simulator);
    expect(imbalance).toEqual(null);
  });
  test("runs as expected on txHash = 0xca0bbc", async () => {
    const transaction = await getTxData(
      "0xca0bbc3551a4e44c31a9fbd29f872f921548d33400e28debb07ffdc5c2d82370"
    );
    const imbalance = await simulateSolverSolution(transaction, simulator);
    expect(imbalance).toMatchSnapshot();
  });
  test("run pipeline on transaction known to fail first simulation", async () => {
    const simFailer = await getTxData(
      "0x82c20f4583fb2a49a1db506ef2a1777a3efc99d90d100f7d2da9ca718de395f2"
    );
    const simulation = (await simulateSolverSolution(simFailer, simulator))!;
    expect(simulation.winningSettlement.simulationBlock + 1).toEqual(
      simulation.reduced.blockNumber
    );
    expect(simulation.winningSettlement.simulationBlock + 1).toEqual(
      simulation.full.blockNumber
    );
  }, 300000);
  test("returns default when transaction fails all attempted blocks", async () => {
    // Fails Tenderly (but apparently does not fail Phalcon).
    const failingSimulation = await getTxData(
      "0x9D5F8748D29893438B01A1CA9EE21A192A760997BCDA1987A9A368DCD733A0D6"
    );
    const simulation = (await simulateSolverSolution(
      failingSimulation,
      simulator
    ))!;
    expect(simulation.full).toEqual(simulation.reduced);
    expect(simulation.full).toEqual({
      blockNumber: -1,
      ethDelta: new Map(),
      gasUsed: 0,
      logs: [],
      simulationID: "failed all 3 simulation attempts",
    });
  }, 300000);
});
describe.skip("completeComposition(transaction, simulator)", () => {
  test("runs as expected on txHash = 0xca0bbc", async () => {
    const transaction = await getTxData(
      "0xca0bbc3551a4e44c31a9fbd29f872f921548d33400e28debb07ffdc5c2d82370"
    );
    const simData = await simulateSolverSolution(transaction, simulator);
    expect(simData).toBeDefined();
    expect(getInternalizedImbalance(simData!)).toEqual([
      {
        amount: -1608243187495153737n,
        token: "0xc02aaa39b223fe8d0a0e5c4f27ead9083c756cc2",
      },
      {
        // THIS DISAGREES WITH PYTHON CODE!
        amount: 218470417n,
        token: "0xa0b86991c6218b36c1d19d4a2e9eb0ce3606eb48",
      },
      {
        amount: 2264567919421268662217n,
        token: "0x6b175474e89094c44da98b954eedeac495271d0f",
      },
    ]);
  });
  test("runs as expected on txHash = 0xc6a48f", async () => {
    const transaction = await getTxData(
      "0xc6a48f8c08dad2742fa225246da2becec44d87c54e5dadb516d34c1cffc3f2d5"
    );
    const simData = await simulateSolverSolution(transaction, simulator);
    expect(simData).toBeDefined();
    expect(getInternalizedImbalance(simData!)).toEqual([
      {
        amount: -3763821350n,
        token: "0xa0b86991c6218b36c1d19d4a2e9eb0ce3606eb48",
      },
      // This is expected but did not appear in the on chain data because
      // this token was not at all involved.
      // (must have been a multi-hop token that was completely avoided)
      {
        amount: 42476141134110n,
        token: "0x7d1afa7b718fb893db30a3abc0cfc608aacfebb0",
      },
      {
        amount: -622410208819002243n,
        token: "0xc02aaa39b223fe8d0a0e5c4f27ead9083c756cc2",
      },
      {
        amount: 2232582627542468223215n,
        token: "0x5a98fcbea516cf06857215779fd812ca3bef1b32",
      },
    ]);
  });
  test("runs as expected on txHash = 0x7a007e", async () => {
    const transaction = await getTxData(
      "0x7a007eb8ad25f5f1f1f36459998ae758b0e699ca69cc7b4c38354d42092651bf"
    );
    const simData = await simulateSolverSolution(transaction, simulator);
    expect(simData).toBeDefined();
    expect(getInternalizedImbalance(simData!)).toEqual([
      {
        token: "0xc02aaa39b223fe8d0a0e5c4f27ead9083c756cc2",
        amount: -95100807345736279n,
      },
      {
        token: "0x64aa3364f17a4d01c6f1751fd97c2bd3d7e7f1d5",
        amount: 14916332565n,
      },
    ]);
  });
  test("runs as expected on txHash = 0x0e9877", async () => {
    const transaction = await getTxData(
      "0x0e9877bff7c9f9fb8516afc857d5bc986f8116bbf6972899c3eb65af4445901e"
    );
    const simData = await simulateSolverSolution(transaction, simulator);
    expect(simData).toBeDefined();
    expect(getInternalizedImbalance(simData!)).toEqual([
      {
        amount: -1694865144280746549n,
        token: "0x6810e776880c02933d47db1b9fc05908e5386b96",
      },
      {
        amount: 121091287566514411n,
        token: "0xc02aaa39b223fe8d0a0e5c4f27ead9083c756cc2",
      },
    ]);
  });
  test("runs as expected on txHash = 0x426690f", async () => {
    const transaction = await getTxData(
      "0x426690f4385bf943dffc12c5e2adbfd793acc1d16b3a8f5fddcd9e3f94a5a20b"
    );
    const simData = await simulateSolverSolution(transaction, simulator);
    expect(simData).toBeDefined();
    expect(getInternalizedImbalance(simData!)).toEqual([
      {
        amount: 5677312578n,
        token: "0xa0b86991c6218b36c1d19d4a2e9eb0ce3606eb48",
      },
      {
        amount: -4480160974861274910720n,
        token: "0x0f2d719407fdbeff09d87557abb7232601fd9f29",
      },
      {
        amount: 1054375308649770183n,
        token: "0xc02aaa39b223fe8d0a0e5c4f27ead9083c756cc2",
      },
    ]);
  });
  test("ETH Transfers - 0x7a007eb", async () => {
    // Transaction contains ETH transfers (but they were not internalized)
    // It is non-trivial to find batches with internalized ETH transfers.
    // However, the tests we have in `accounting.spec` should demonstrate we are prepared to handle them.
    const transaction = await getTxData(
      "0x7a007eb8ad25f5f1f1f36459998ae758b0e699ca69cc7b4c38354d42092651bf"
    );
    const simData = await simulateSolverSolution(transaction, simulator);
    expect(simData).toBeDefined();
    expect(getInternalizedImbalance(simData!)).toEqual([
      {
        amount: -95100807345736279n,
        token: "0xc02aaa39b223fe8d0a0e5c4f27ead9083c756cc2",
      },
      {
        amount: 14916332565n,
        token: "0x64aa3364f17a4d01c6f1751fd97c2bd3d7e7f1d5",
      },
    ]);
  });
});
