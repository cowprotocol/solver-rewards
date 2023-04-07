import {
  isTenderlySimulationResponse,
  parseTenderlySimulation,
  TenderlySimulator,
} from "../src/simulate/tenderly";
import { address as SETTLEMENT_CONTRACT_ADDRESS } from "@cowprotocol/contracts/deployments/mainnet/GPv2Settlement.json";
import { config as envConfig } from "dotenv";

const oneAddress = "0x0000000000000000000000000000000000000001";

const invalidSimulator = new TenderlySimulator(
  "INVALID_USER",
  "INVALID_PROJECT",
  "INVALID_KEY"
);
envConfig();
// Note that simulator will also be invalid if the env vars are not set.
const simulator = new TenderlySimulator(
  process.env["TENDERLY_USER"] || "TENDERLY_USER",
  process.env["TENDERLY_PROJECT"] || "TENDERLY_PROJECT",
  process.env["TENDERLY_ACCESS_KEY"] || "TENDERLY_ACCESS_KEY"
);
describe("Tenderly Simulator", () => {
  test.skip("simulate() returns expected output on successful simulation", async () => {
    const simulation = await simulator.simulate({
      callData:
        "0x13d79a0b000000000000000000000000000000000000000000000000000000000000008000000000000000000000000000000000000000000000000000000000000000e00000000000000000000000000000000000000000000000000000000000000140000000000000000000000000000000000000000000000000000000000000036000000000000000000000000000000000000000000000000000000000000000020000000000000000000000003432b6a60d23ca0dfca7761b7ab56459d9c964d00000000000000000000000006b175474e89094c44da98b954eedeac495271d0f000000000000000000000000000000000000000000000000000000000000000200000000000000000000000000000000000000000000000000000009e1a51c6b00000000000000000000000000000000000000000000000000000002540be4000000000000000000000000000000000000000000000000000000000000000001000000000000000000000000000000000000000000000000000000000000002000000000000000000000000000000000000000000000000000000000000000010000000000000000000000000000000000000000000000000000000000000000000000000000000000000000e2b424053b9ebfcedf89ecb8bf2972974e98700c00000000000000000000000000000000000000000000006c0b439bc588511000000000000000000000000000000000000000000000000019629e5fa65ea1706b0000000000000000000000000000000000000000000000000000000063af639ec86d3a0def4d16bd04317645da9ae1d6871726d8adf83a0695447f8ee5c63d12000000000000000000000000000000000000000000000000604fbfc634eef000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000006c0b439bc58851100000000000000000000000000000000000000000000000000000000000000001600000000000000000000000000000000000000000000000000000000000000041d6f2b85ab927ca9078c1081587fe4ea7ec72a9e1ef3ed826649e8fa063bafb45643196adc29f3c13403865f063131bb2a5a293483423c810ea56dc764e25e2971c00000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000006000000000000000000000000000000000000000000000000000000000000000800000000000000000000000000000000000000000000000000000000000000260000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000010000000000000000000000000000000000000000000000000000000000000020000000000000000000000000d9e1ce17f2641f24ae83637ab66a2cca9c378b9f0000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000006000000000000000000000000000000000000000000000000000000000000001048803dbee000000000000000000000000000000000000000000000018ba53f5c7f06ef117000000000000000000000000000000000000000000000000166c0a97dd56bfd500000000000000000000000000000000000000000000000000000000000000a00000000000000000000000009008d19f58aabd9ed0d60971565aa8510560ab41ffffffffffffffffffffffffffffffffffffffffffffffffffffffffffffffff0000000000000000000000000000000000000000000000000000000000000002000000000000000000000000c02aaa39b223fe8d0a0e5c4f27ead9083c756cc20000000000000000000000003432b6a60d23ca0dfca7761b7ab56459d9c964d0000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000",
      sender: "0xa21740833858985e4d801533a808786d3647fb83",
      value: "0",
      contractAddress: SETTLEMENT_CONTRACT_ADDRESS,
      blockNumber: 16300366,
    });
    expect(simulation).toMatchSnapshot();
  });
  test.skip("simulate() returns expected output on failed simulation", async () => {
    await expect(
      simulator.simulate({
        callData: "0x",
        sender: oneAddress,
        value: "0",
        contractAddress: SETTLEMENT_CONTRACT_ADDRESS,
        blockNumber: 16300366,
      })
    ).rejects.toThrow();
  });
  test("simulate() returns expected output with invalid credentials", async () => {
    await expect(
      invalidSimulator.simulate({
        callData: "0x",
        contractAddress: "0x",
        sender: "0x",
        value: "0",
      })
    ).rejects.toThrow('Invalid Response ""');
  });
  test("simulate() throws bad request error", async () => {
    const badRequestSimulator = new TenderlySimulator("", "", "");
    await expect(
      badRequestSimulator.simulate({
        callData: "0x",
        contractAddress: "0x",
        sender: "0x",
        value: "0",
      })
    ).rejects.toThrow("Request failed with status code 401");
  });

  test("parseTenderlySimulation() operates as expected", () => {
    const mockSimulation = {
      // Test Data excludes irrelevant fields.
      transaction: {
        hash: "0xHASH",
        transaction_info: {
          block_number: 5,
          logs: [
            {
              raw: {
                address: "0xADDRESS",
                data: "0xDATA",
                topics: ["0xTOPIC_1"],
              },
            },
          ],
        },
      },
    };
    expect(parseTenderlySimulation(mockSimulation)).toEqual({
      blockNumber: 5,
      logs: [
        {
          address: "0xADDRESS",
          data: "0xDATA",
          topics: ["0xTOPIC_1"],
        },
      ],
      txHash: "0xHASH",
    });
  });
  test("isTenderlySimulationResponse() returns false", () => {
    expect(
      isTenderlySimulationResponse({
        transaction: {
          hash: "",
          transaction_info: {
            block_number: 0,
            // TODO - No Logs... probably shouldn't fail here!
            logs: null,
          },
        },
      })
    ).toBe(false);
  });

  test("parseSimulation() operates as expected", () => {
    const mockSimulation = {
      // Test Data excludes irrelevant fields.
      transaction: {
        hash: "0xa7b2f2ff14a780504c97aeb484bfd7560486241c00f066395e1e8c2e9d99ffd3",
        transaction_info: {
          block_number: 16300366,
          logs: [
            {
              raw: {
                address: "0x9008d19f58aabd9ed0d60971565aa8510560ab41",
                data: "0x0000000000000000000000006b175474e89094c44da98b954eedeac495271d0f0000000000000000000000003432b6a60d23ca0dfca7761b7ab56459d9c964d000000000000000000000000000000000000000000000006c6b935b8bbd400000000000000000000000000000000000000000000000000019753399721b8078ee000000000000000000000000000000000000000000000000604fbfc634eef00000000000000000000000000000000000000000000000000000000000000000c00000000000000000000000000000000000000000000000000000000000000038bf293f652b46fe85a15838d7ff736add1b6098ed1c143f3902869d325f9e0069e2b424053b9ebfcedf89ecb8bf2972974e98700c63af639e0000000000000000",
                topics: [
                  "0xa07a543ab8a018198e99ca0184c93fe9050a79400a0a723441f84de1d972cc17",
                  "0x000000000000000000000000e2b424053b9ebfcedf89ecb8bf2972974e98700c",
                ],
              },
            },
            {
              raw: {
                address: "0x6b175474e89094c44da98b954eedeac495271d0f",
                data: "0x00000000000000000000000000000000000000000000006c6b935b8bbd400000",
                topics: [
                  "0xddf252ad1be2c89b69c2b068fc378daa952ba7f163c4a11628f55a4df523b3ef",
                  "0x000000000000000000000000e2b424053b9ebfcedf89ecb8bf2972974e98700c",
                  "0x0000000000000000000000009008d19f58aabd9ed0d60971565aa8510560ab41",
                ],
              },
            },
          ],
        },
      },
    };
    expect(invalidSimulator.parseSimulation(mockSimulation)).toMatchSnapshot();
  });
  test("parseSimulation() throws as expected.", () => {
    const invalidSimulator = new TenderlySimulator("", "", "");
    expect(() => invalidSimulator.parseSimulation({})).toThrow(
      "Invalid simulation data {}"
    );
  });
});
