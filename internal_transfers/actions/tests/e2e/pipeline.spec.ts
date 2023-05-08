import { TenderlySimulator } from "../../src/simulate/tenderly";
import { internalizedTokenImbalance } from "../../src/pipeline";
import { getDB } from "../../src/database";
import { getTxData } from "./helper";

const { TENDERLY_USER, TENDERLY_PROJECT, TENDERLY_ACCESS_KEY } = process.env;

const simulator = new TenderlySimulator(
  TENDERLY_USER || "INVALID_USER",
  TENDERLY_PROJECT || "TENDERLY_PROJECT",
  TENDERLY_ACCESS_KEY || "TENDERLY_ACCESS_KEY"
);

const db = getDB("postgresql://postgres:postgres@localhost:5432/postgres");

describe.skip("Run Full Pipeline", () => {
  test("run pipeline on notInternalized transaction", async () => {
    const notInternalized = await getTxData(
      "0x0f86c06d9ace6a88644db6b654a904aa62c82305023e094ce49650467c91bd6e"
    );
    await internalizedTokenImbalance(notInternalized, db, simulator);
  }, 300000);
  test("run pipeline on batch with internalized transfers", async () => {
    const internalized = await getTxData(
      "0xDCD5CF12340B50ACC04DBE7E14A903BE373456C81E4DB20DD84CF0301F6AB869"
    );
    await internalizedTokenImbalance(internalized, db, simulator);
  }, 300000);

  test("run pipeline on transaction with unavailable competition data", async () => {
    const unavailable = await getTxData(
      "0xe6a0fbad3f9571e7614dbbc1d65d523cbeb6929b59bd20cde80ac791899fccfb"
    );
    await internalizedTokenImbalance(unavailable, db, simulator);
  }, 300000);
});
