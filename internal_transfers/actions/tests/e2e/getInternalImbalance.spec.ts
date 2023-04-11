import { getInternalImbalance, MinimalTxData } from "../../src/accounting";
import { TenderlySimulator } from "../../src/simulate/tenderly";
import { ethers } from "ethers";

const simulator = new TenderlySimulator(
  process.env["TENDERLY_USER"] || "INVALID_USER",
  process.env["TENDERLY_PROJECT"] || "TENDERLY_PROJECT",
  process.env["TENDERLY_ACCESS_KEY"] || "TENDERLY_ACCESS_KEY"
);

async function TxDataFromHash(txHash: string): Promise<MinimalTxData> {
  const provider = ethers.getDefaultProvider(
    process.env["NODE_URL"] || "NODE_URL"
  );
  const transaction = await provider.getTransactionReceipt(txHash);
  if (transaction === null) {
    throw new Error(`invalid transaction hash ${txHash} - try again`);
  }
  const { from, hash, logs } = transaction;
  const tenderlyLogs = logs.map((log) => {
    const { address, data, topics } = log;
    return {
      address,
      data,
      // had to Map it to make a copy of a readonly field.
      topics: topics.map((value) => value),
    };
  });

  return {
    from,
    hash,
    logs: tenderlyLogs,
  };
}
describe.skip("getInternalImbalance(transaction, simulator)", () => {
  test.skip("throws when no competition found", async () => {
    const txHash =
      "0x08100e7ba81be84ee0bdce43db6640e2f992ec9991a740a689e97d20dea9dafa";
    const transaction = await TxDataFromHash(txHash);
    await expect(getInternalImbalance(transaction, simulator)).rejects.toThrow(
      `No competition found for ${txHash}`
    );
  });
  test.skip("runs as expected on legit txHash with no imbalance", async () => {
    const txHash =
      "0x3b2e9675b6d71a34e9b7f4abb4c9e80922be311076fcbb345d7da9d91a05e048";
    const transaction = await TxDataFromHash(txHash);
    const imbalance = await getInternalImbalance(transaction, simulator);
    expect(imbalance).toEqual([]);
  });
  test.skip("runs as expected on legit txHash - 0xca0bbc", async () => {
    const txHash =
      "0xca0bbc3551a4e44c31a9fbd29f872f921548d33400e28debb07ffdc5c2d82370";
    const transaction = await TxDataFromHash(txHash);
    const imbalance = await getInternalImbalance(transaction, simulator);
    expect(imbalance).toEqual([
      {
        amount: -1608243187495153737n,
        token: "0xc02aaa39b223fe8d0a0e5c4f27ead9083c756cc2",
      },
      {
        // THIS DISAGREES WITH PYTHON CODE!
        amount: 230686181n,
        token: "0xa0b86991c6218b36c1d19d4a2e9eb0ce3606eb48",
      },
      {
        amount: 2264567919421268662217n,
        token: "0x6b175474e89094c44da98b954eedeac495271d0f",
      },
    ]);
  });
  test.skip("runs as expected on legit txHash - 0xc6a48f", async () => {
    const txHash =
      "0xc6a48f8c08dad2742fa225246da2becec44d87c54e5dadb516d34c1cffc3f2d5";
    const transaction = await TxDataFromHash(txHash);
    const imbalance = await getInternalImbalance(transaction, simulator);
    expect(imbalance).toEqual([
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
  test.skip("runs as expected on legit txHash - 0x7a007e", async () => {
    const txHash =
      "0x7a007eb8ad25f5f1f1f36459998ae758b0e699ca69cc7b4c38354d42092651bf";
    const transaction = await TxDataFromHash(txHash);
    const imbalance = await getInternalImbalance(transaction, simulator);
    expect(imbalance).toEqual([
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
  test.skip("runs as expected on legit txHash - 0x0e9877", async () => {
    const txHash =
      "0x0e9877bff7c9f9fb8516afc857d5bc986f8116bbf6972899c3eb65af4445901e";
    const transaction = await TxDataFromHash(txHash);
    const imbalance = await getInternalImbalance(transaction, simulator);
    expect(imbalance).toEqual([
      {
        token: "0x6810e776880c02933d47db1b9fc05908e5386b96",
        amount: -1694865144280746549n,
      },
      {
        token: "0x00a8b738e453ffd858a7edf03bccfe20412f0eb0",
        amount: -1945523048541962118749n,
      },
      {
        token: "0xc02aaa39b223fe8d0a0e5c4f27ead9083c756cc2",
        amount: 99902973634572547n,
      },
    ]);
  });
  test.skip("runs as expected on legit txHash - 0x426690f", async () => {
    const txHash =
      "0x426690f4385bf943dffc12c5e2adbfd793acc1d16b3a8f5fddcd9e3f94a5a20b";
    const transaction = await TxDataFromHash(txHash);
    const imbalance = await getInternalImbalance(transaction, simulator);
    expect(imbalance).toEqual([
      {
        token: "0xa0b86991c6218b36c1d19d4a2e9eb0ce3606eb48",
        // THIS DISAGREES WITH PYTHON CODE!
        amount: 5675883800n,
      },
      {
        token: "0x0f2d719407fdbeff09d87557abb7232601fd9f29",
        amount: -4480160974861274910720n,
      },
      {
        token: "0xc02aaa39b223fe8d0a0e5c4f27ead9083c756cc2",
        amount: 1054375308649770183n,
      },
    ]);
  });
});
