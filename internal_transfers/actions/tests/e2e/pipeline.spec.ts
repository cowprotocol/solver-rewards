import { TenderlySimulator } from "../../src/simulate/tenderly";
import { internalizedTokenImbalance } from "../../src/pipeline";
import { getDB } from "../../src/database";

const { TENDERLY_USER, TENDERLY_PROJECT, TENDERLY_ACCESS_KEY } = process.env;

const simulator = new TenderlySimulator(
  TENDERLY_USER || "INVALID_USER",
  TENDERLY_PROJECT || "TENDERLY_PROJECT",
  TENDERLY_ACCESS_KEY || "TENDERLY_ACCESS_KEY"
);

const db = getDB("postgresql://postgres:postgres@localhost:5432/postgres");

describe("Run Full Pipeline", () => {
  test("run pipeline on notInternalized transaction", async () => {
    // TODO - unavailable (i.e. null response from orderbook):
    //  choose very old transaction -- pre July 2022
    const notInternalized = {
      blockNumber: 15182101,
      from: "0xe9ae2d792f981c53ea7f6493a17abf5b2a45a86b",
      hash: "0x0f86c06d9ace6a88644db6b654a904aa62c82305023e094ce49650467c91bd6e",
      logs: [
        {
          address: "0x9008d19f58aabd9ed0d60971565aa8510560ab41",
          data: "0x",
          topics: [
            "0x40338ce1a7c49204f0099533b1e9a7ee0a3d261f84974ab7af36105b8c4e9db4",
            "0x000000000000000000000000e9ae2d792f981c53ea7f6493a17abf5b2a45a86b",
          ],
        },
      ],
    };
    await internalizedTokenImbalance(notInternalized, db, simulator);
  }, 300000);
  test("run pipeline on batch with internalized transfers", async () => {
    const internalized = {
      blockNumber: 16310552,
      from: "0x97EC0A17432D71A3234EF7173C6B48A2C0940896",
      hash: "0xDCD5CF12340B50ACC04DBE7E14A903BE373456C81E4DB20DD84CF0301F6AB869",
      logs: [
        {
          address: "0x9008d19f58aabd9ed0d60971565aa8510560ab41",
          data: "0x",
          topics: [
            "0x40338ce1a7c49204f0099533b1e9a7ee0a3d261f84974ab7af36105b8c4e9db4",
            "0x00000000000000000000000097EC0A17432D71A3234EF7173C6B48A2C0940896",
          ],
        },
      ],
    };
    await internalizedTokenImbalance(internalized, db, simulator);
  }, 300000);

  test("run pipeline on transaction with unavailable competition data", async () => {
    // TODO - unavailable (i.e. null response from orderbook):
    //  choose very old transaction -- pre July 2022
    // const unavailable = {
    //     blockNumber: 15182101,
    //     from: "0xe9ae2d792f981c53ea7f6493a17abf5b2a45a86b",
    //     hash: "0x0f86c06d9ace6a88644db6b654a904aa62c82305023e094ce49650467c91bd6e",
    //     logs: [
    //       {
    //         address: "0x9008d19f58aabd9ed0d60971565aa8510560ab41",
    //         data: "0x",
    //         topics: [
    //           "0x40338ce1a7c49204f0099533b1e9a7ee0a3d261f84974ab7af36105b8c4e9db4",
    //           "0x000000000000000000000000e9ae2d792f981c53ea7f6493a17abf5b2a45a86b",
    //         ],
    //       },
    //     ],
    //   };
    // await internalizedTokenImbalance(unavailable, db, simulator);
  }, 300000);
});
