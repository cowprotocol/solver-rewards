import { TenderlySimulator } from "../../src/simulate/tenderly";
import { internalizedTokenImbalance } from "../../src/pipeline";
import { getDB } from "../../src/database";
import { getTxData } from "./helper";
import { ethers } from "ethers";

const { TENDERLY_USER, TENDERLY_PROJECT, TENDERLY_ACCESS_KEY, NODE_URL } =
  process.env;

const simulator = new TenderlySimulator(
  TENDERLY_USER || "INVALID_USER",
  TENDERLY_PROJECT || "TENDERLY_PROJECT",
  TENDERLY_ACCESS_KEY || "TENDERLY_ACCESS_KEY"
);
const provider = ethers.getDefaultProvider(NODE_URL!);

const db = getDB("postgresql://postgres:postgres@localhost:5432/postgres");

describe.skip("Run Full Pipeline", () => {
  test("run pipeline on non-internalized transaction", async () => {
    const notInternalized = await getTxData(
      "0x0f86c06d9ace6a88644db6b654a904aa62c82305023e094ce49650467c91bd6e"
    );
    await expect(
      internalizedTokenImbalance(notInternalized, db, simulator, provider)
    ).resolves.not.toThrowError();
  }, 300000);
  test("run pipeline on batch with internalized transfers", async () => {
    const internalized = await getTxData(
      "0xDCD5CF12340B50ACC04DBE7E14A903BE373456C81E4DB20DD84CF0301F6AB869"
    );
    await expect(
      internalizedTokenImbalance(internalized, db, simulator, provider)
    ).resolves.not.toThrowError();
  }, 300000);

  test("throws on unavailable competition data for successful transaction", async () => {
    const txHash =
      "0xe6a0fbad3f9571e7614dbbc1d65d523cbeb6929b59bd20cde80ac791899fccfb";
    const unavailable = await getTxData(txHash);
    await expect(
      internalizedTokenImbalance(unavailable, db, simulator, provider)
    ).rejects.toThrow(`No competition found for ${txHash}`);
  }, 300000);

  test("resolves on unavailable competition data for failed transaction", async () => {
    const txHash =
      "0x1231f2c9b519adc5ae7db17c84418e140553e234b2868d6b1d7f66a692683e73";
    const unavailable = await getTxData(txHash);
    await expect(
      internalizedTokenImbalance(unavailable, db, simulator, provider)
    ).resolves.not.toThrowError();
  }, 300000);
});
