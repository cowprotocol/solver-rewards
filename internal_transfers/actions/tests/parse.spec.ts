import {
  partitionEventLogs,
  tryParseERC20Transfer,
  tryParseSettlementEventLog,
  tryParseWethAction,
  WETH_TOKEN_ADDRESS,
} from "../src/parse";
import { address as SETTLEMENT_CONTRACT_ADDRESS } from "@cowprotocol/contracts/deployments/mainnet/GPv2Settlement.json";
import { isSettlementEvent, isTradeEvent } from "../src/models";
import { ethers } from "ethers";

const SETTLEMENT_EVENT_TOPIC =
  "0x40338ce1a7c49204f0099533b1e9a7ee0a3d261f84974ab7af36105b8c4e9db4";
const TRANSFER_EVENT_TOPIC =
  "0xddf252ad1be2c89b69c2b068fc378daa952ba7f163c4a11628f55a4df523b3ef";
const TRADE_EVENT_TOPIC =
  "0xa07a543ab8a018198e99ca0184c93fe9050a79400a0a723441f84de1d972cc17";
// Aka WETH Withdrawal
const ETH_UNWRAP_EVENT_TOPIC =
  "0x7fcf532c15f0a6db0bd6d0e038bea71d30d808c7d98cb3bf7268a95bf5081b65";
// Aka WETH Deposit
const ETH_WRAP_EVENT_TOPIC =
  "0xe1fffcc4923d04b559f4d29a8bfc6cda04eb5b0d3c460751c2402c5c5cc9109c";
function addressToTopic(address: string): string {
  return "0x000000000000000000000000" + address.slice(2);
}
describe("partitionEventLogs(logs)", () => {
  test("parses SimulationData event logs", async () => {
    const simulationData = {
      blockNumber: 16300366,
      txHash:
        "0xa7b2f2ff14a780504c97aeb484bfd7560486241c00f066395e1e8c2e9d99ffd3",
      logs: [
        {
          address: "0x9008d19f58aabd9ed0d60971565aa8510560ab41",
          data: "0x0000000000000000000000006b175474e89094c44da98b954eedeac495271d0f0000000000000000000000003432b6a60d23ca0dfca7761b7ab56459d9c964d000000000000000000000000000000000000000000000006c6b935b8bbd400000000000000000000000000000000000000000000000000019753399721b8078ee000000000000000000000000000000000000000000000000604fbfc634eef00000000000000000000000000000000000000000000000000000000000000000c00000000000000000000000000000000000000000000000000000000000000038bf293f652b46fe85a15838d7ff736add1b6098ed1c143f3902869d325f9e0069e2b424053b9ebfcedf89ecb8bf2972974e98700c63af639e0000000000000000",
          topics: [
            "0xa07a543ab8a018198e99ca0184c93fe9050a79400a0a723441f84de1d972cc17",
            "0x000000000000000000000000e2b424053b9ebfcedf89ecb8bf2972974e98700c",
          ],
        },
        {
          address: "0x6b175474e89094c44da98b954eedeac495271d0f",
          data: "0x00000000000000000000000000000000000000000000006c6b935b8bbd400000",
          topics: [
            "0xddf252ad1be2c89b69c2b068fc378daa952ba7f163c4a11628f55a4df523b3ef",
            "0x000000000000000000000000e2b424053b9ebfcedf89ecb8bf2972974e98700c",
            "0x0000000000000000000000009008d19f58aabd9ed0d60971565aa8510560ab41",
          ],
        },
        {
          address: "0xc02aaa39b223fe8d0a0e5c4f27ead9083c756cc2",
          data: "0x00000000000000000000000000000000000000000000000016664e9c50f84b06",
          topics: [
            "0xddf252ad1be2c89b69c2b068fc378daa952ba7f163c4a11628f55a4df523b3ef",
            "0x0000000000000000000000009008d19f58aabd9ed0d60971565aa8510560ab41",
            "0x00000000000000000000000061eb53ee427ab4e007d78a9134aacb3101a2dc23",
          ],
        },
        {
          address: "0x3432b6a60d23ca0dfca7761b7ab56459d9c964d0",
          data: "0x0000000000000000000000000000000000000000000032f0a8c0e7cc613fb4eb0000000000000000000000000000000000000000000032d7ee6cf20470d0c3d4",
          topics: [
            "0x3eaa1c4be29b4a4c60e00300b5a17a8ec6c982b5b0ad5870cc84ebdc3b24d68e",
            "0x00000000000000000000000061eb53ee427ab4e007d78a9134aacb3101a2dc23",
          ],
        },
        {
          address: "0x3432b6a60d23ca0dfca7761b7ab56459d9c964d0",
          data: "0x000000000000000000000000000000000000000000000000d23441dafae571160000000000000000000000000000000000000000000000198c8837a2eb54622d",
          topics: [
            "0x3eaa1c4be29b4a4c60e00300b5a17a8ec6c982b5b0ad5870cc84ebdc3b24d68e",
            "0x0000000000000000000000009008d19f58aabd9ed0d60971565aa8510560ab41",
          ],
        },
        {
          address: "0x3432b6a60d23ca0dfca7761b7ab56459d9c964d0",
          data: "0x000000000000000000000000000000000000000000000018ba53f5c7f06ef117",
          topics: [
            "0xddf252ad1be2c89b69c2b068fc378daa952ba7f163c4a11628f55a4df523b3ef",
            "0x00000000000000000000000061eb53ee427ab4e007d78a9134aacb3101a2dc23",
            "0x0000000000000000000000009008d19f58aabd9ed0d60971565aa8510560ab41",
          ],
        },
        {
          address: "0x61eb53ee427ab4e007d78a9134aacb3101a2dc23",
          data: "0x0000000000000000000000000000000000000000000032d7ee6cf20470d0c3d400000000000000000000000000000000000000000000002e0177b105e865b03b",
          topics: [
            "0x1c411e9a96e071241c2f21f7726b17ae89e3cab4c78be50e062b03a9fffbbad1",
          ],
        },
        {
          address: "0x61eb53ee427ab4e007d78a9134aacb3101a2dc23",
          data: "0x000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000016664e9c50f84b06000000000000000000000000000000000000000000000018ba53f5c7f06ef1170000000000000000000000000000000000000000000000000000000000000000",
          topics: [
            "0xd78ad95fa46c994b6551d0da85fc275fe613ce37657fb8d5e3d130840159d822",
            "0x000000000000000000000000d9e1ce17f2641f24ae83637ab66a2cca9c378b9f",
            "0x0000000000000000000000009008d19f58aabd9ed0d60971565aa8510560ab41",
          ],
        },
        {
          address: "0x9008d19f58aabd9ed0d60971565aa8510560ab41",
          data: "0x00000000000000000000000000000000000000000000000000000000000000008803dbee00000000000000000000000000000000000000000000000000000000",
          topics: [
            "0xed99827efb37016f2275f98c4bcf71c7551c75d59e9b450f79fa32e60be672c2",
            "0x000000000000000000000000d9e1ce17f2641f24ae83637ab66a2cca9c378b9f",
          ],
        },
        {
          address: "0x3432b6a60d23ca0dfca7761b7ab56459d9c964d0",
          data: "0x0000000000000000000000000000000000000000000000198c8837a2eb54622d00000000000000000000000000000000000000000000000017549e30cfd3e93f",
          topics: [
            "0x3eaa1c4be29b4a4c60e00300b5a17a8ec6c982b5b0ad5870cc84ebdc3b24d68e",
            "0x0000000000000000000000009008d19f58aabd9ed0d60971565aa8510560ab41",
          ],
        },
        {
          address: "0x3432b6a60d23ca0dfca7761b7ab56459d9c964d0",
          data: "0x0000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000019753399721b8078ee",
          topics: [
            "0x3eaa1c4be29b4a4c60e00300b5a17a8ec6c982b5b0ad5870cc84ebdc3b24d68e",
            "0x000000000000000000000000e2b424053b9ebfcedf89ecb8bf2972974e98700c",
          ],
        },
        {
          address: "0x3432b6a60d23ca0dfca7761b7ab56459d9c964d0",
          data: "0x000000000000000000000000000000000000000000000019753399721b8078ee",
          topics: [
            "0xddf252ad1be2c89b69c2b068fc378daa952ba7f163c4a11628f55a4df523b3ef",
            "0x0000000000000000000000009008d19f58aabd9ed0d60971565aa8510560ab41",
            "0x000000000000000000000000e2b424053b9ebfcedf89ecb8bf2972974e98700c",
          ],
        },
        {
          address: "0x9008d19f58aabd9ed0d60971565aa8510560ab41",
          data: "0x",
          topics: [
            "0x40338ce1a7c49204f0099533b1e9a7ee0a3d261f84974ab7af36105b8c4e9db4",
            "0x000000000000000000000000a21740833858985e4d801533a808786d3647fb83",
          ],
        },
        // WETH Deposit
        {
          address: "0xc02aaa39b223fe8d0a0e5c4f27ead9083c756cc2",
          topics: [
            ETH_WRAP_EVENT_TOPIC,
            addressToTopic(SETTLEMENT_CONTRACT_ADDRESS),
          ],
          data: "0x00000000000000000000000000000000000000000000000000354a6ba7a18000",
        },
        // WETH Withdrawal
        {
          address: "0xc02aaa39b223fe8d0a0e5c4f27ead9083c756cc2",
          topics: [
            ETH_UNWRAP_EVENT_TOPIC,
            addressToTopic(SETTLEMENT_CONTRACT_ADDRESS),
          ],
          data: "0x0000000000000000000000000000000000000000000000001ca811856c2c5a63",
        },
      ],
    };
    const { trades, transfers, settlements } = partitionEventLogs(
      simulationData.logs
    );

    expect(trades).toEqual([
      { owner: "0xE2b424053b9ebFCEdF89ECB8Bf2972974E98700C" },
    ]);
    expect(transfers).toEqual([
      {
        amount: BigInt("2000000000000000000000"),
        from: "0xE2b424053b9ebFCEdF89ECB8Bf2972974E98700C",
        to: "0x9008D19f58AAbD9eD0D60971565AA8510560ab41",
        token: "0x6b175474e89094c44da98b954eedeac495271d0f",
      },
      {
        amount: BigInt("1614063949739215622"),
        from: "0x9008D19f58AAbD9eD0D60971565AA8510560ab41",
        to: "0x61eB53ee427aB4E007d78A9134AaCb3101A2DC23",
        token: "0xc02aaa39b223fe8d0a0e5c4f27ead9083c756cc2",
      },
      {
        amount: BigInt("456148202922231918871"),
        from: "0x61eB53ee427aB4E007d78A9134AaCb3101A2DC23",
        to: "0x9008D19f58AAbD9eD0D60971565AA8510560ab41",
        token: "0x3432b6a60d23ca0dfca7761b7ab56459d9c964d0",
      },
      {
        amount: BigInt("469613864284355328238"),
        from: "0x9008D19f58AAbD9eD0D60971565AA8510560ab41",
        to: "0xE2b424053b9ebFCEdF89ECB8Bf2972974E98700C",
        token: "0x3432b6a60d23ca0dfca7761b7ab56459d9c964d0",
      },
      {
        amount: 15000000000000000n,
        from: "0x0000000000000000000000000000000000000000",
        to: "0x9008D19f58AAbD9eD0D60971565AA8510560ab41",
        token: "0xc02aaa39b223fe8d0a0e5c4f27ead9083c756cc2",
      },
      {
        amount: 2064919693892541027n,
        from: "0x9008D19f58AAbD9eD0D60971565AA8510560ab41",
        to: "0x0000000000000000000000000000000000000000",
        token: "0xc02aaa39b223fe8d0a0e5c4f27ead9083c756cc2",
      },
    ]);
    expect(settlements).toEqual([
      {
        logIndex: 12,
        solver: "0xA21740833858985e4D801533a808786d3647Fb83",
      },
    ]);
  });
});

describe("tryParseSettlementEvent(log, index)", () => {
  test("parses Trade Event", () => {
    const tradeOwner = "0xd5553C9726EA28e7EbEDfe9879cF8aB4d061dbf0";
    const tradeLog = {
      address: SETTLEMENT_CONTRACT_ADDRESS,
      data: "0x0000000000000000000000006b175474e89094c44da98b954eedeac495271d0f0000000000000000000000003432b6a60d23ca0dfca7761b7ab56459d9c964d000000000000000000000000000000000000000000000006c6b935b8bbd400000000000000000000000000000000000000000000000000019753399721b8078ee000000000000000000000000000000000000000000000000604fbfc634eef00000000000000000000000000000000000000000000000000000000000000000c00000000000000000000000000000000000000000000000000000000000000038bf293f652b46fe85a15838d7ff736add1b6098ed1c143f3902869d325f9e0069e2b424053b9ebfcedf89ecb8bf2972974e98700c63af639e0000000000000000",
      topics: [TRADE_EVENT_TOPIC, addressToTopic(tradeOwner)],
    };
    const tradeEvent = tryParseSettlementEventLog(tradeLog, 1);
    expect(isTradeEvent(tradeEvent)).toStrictEqual(true);
    expect(isSettlementEvent(tradeEvent)).toStrictEqual(false);
    expect(tradeEvent).toStrictEqual({ owner: tradeOwner });
  });
  test("parses Settlement Event", () => {
    const solver = "0xb20B86C4e6DEEB432A22D773a221898bBBD03036";
    const settlementLog = {
      address: SETTLEMENT_CONTRACT_ADDRESS,
      topics: [SETTLEMENT_EVENT_TOPIC, addressToTopic(solver)],
      data: "0x",
    };
    const logIndex = 1;
    const settlementEvent = tryParseSettlementEventLog(settlementLog, logIndex);
    expect(isTradeEvent(settlementEvent)).toStrictEqual(false);
    expect(isSettlementEvent(settlementEvent)).toStrictEqual(true);
    expect(settlementEvent).toStrictEqual({ solver, logIndex });
  });
  test("parses Interaction Event as null", () => {
    const nullEventLog = {
      address: SETTLEMENT_CONTRACT_ADDRESS,
      topics: [
        "0xed99827efb37016f2275f98c4bcf71c7551c75d59e9b450f79fa32e60be672c2",
        addressToTopic("0xF6a94dfD0E6ea9ddFdFfE4762Ad4236576136613"),
      ],
      data: "0x0000000000000000000000000000000000000000000000000000000000000000f021092900000000000000000000000000000000000000000000000000000000",
    };
    const nullEvent = tryParseSettlementEventLog(nullEventLog, 0);
    expect(nullEvent).toStrictEqual(null);
  });
});

describe("tryParseTransferEvent(logs)", () => {
  test("parses Transfer Event", () => {
    const address = "0x0000000000000000000000000000000000000001";
    const transferLog = {
      address: WETH_TOKEN_ADDRESS,
      topics: [
        TRANSFER_EVENT_TOPIC,
        addressToTopic(address),
        addressToTopic(SETTLEMENT_CONTRACT_ADDRESS),
      ],
      data: "0x0000000000000000000000000000000000000000000000000000000000001000",
    };
    const transferEvent = tryParseERC20Transfer(transferLog);

    expect(transferEvent).toEqual({
      amount: BigInt("4096"),
      from: address,
      to: SETTLEMENT_CONTRACT_ADDRESS,
      token: WETH_TOKEN_ADDRESS,
    });
  });
  test("parses Non Transfer Event as null", () => {
    const nonTransferEvent = {
      address: "0xc02aaa39b223fe8d0a0e5c4f27ead9083c756cc2",
      topics: [
        "0x7fcf532c15f0a6db0bd6d0e038bea71d30d808c7d98cb3bf7268a95bf5081b65",
        "0x0000000000000000000000009008d19f58aabd9ed0d60971565aa8510560ab41",
      ],
      data: "0x",
    };
    const nullEvent = tryParseERC20Transfer(nonTransferEvent);
    expect(nullEvent).toStrictEqual(null);
  });
});

describe("tryParseWethAction(logs)", () => {
  test("parses Withdrawal Event Outgoing Transfer", () => {
    const withdrawalEventLog = {
      address: "0xc02aaa39b223fe8d0a0e5c4f27ead9083c756cc2",
      topics: [
        ETH_UNWRAP_EVENT_TOPIC,
        addressToTopic(SETTLEMENT_CONTRACT_ADDRESS),
      ],
      data: "0x0000000000000000000000000000000000000000000000001ca811856c2c5a63",
    };
    const outgoingWethTransfer = tryParseWethAction(withdrawalEventLog);
    expect(outgoingWethTransfer).toStrictEqual({
      amount: 2064919693892541027n,
      from: SETTLEMENT_CONTRACT_ADDRESS,
      to: ethers.ZeroAddress,
      token: WETH_TOKEN_ADDRESS,
    });
  });
  test("parses Deposit Event as Incoming Transfer", () => {
    const depositEventLog = {
      address: "0xc02aaa39b223fe8d0a0e5c4f27ead9083c756cc2",
      topics: [
        ETH_WRAP_EVENT_TOPIC,
        addressToTopic(SETTLEMENT_CONTRACT_ADDRESS),
      ],
      data: "0x00000000000000000000000000000000000000000000000000354a6ba7a18000",
    };
    const incomingWethTransfer = tryParseWethAction(depositEventLog);
    expect(incomingWethTransfer).toStrictEqual({
      amount: 15000000000000000n,
      from: ethers.ZeroAddress,
      to: SETTLEMENT_CONTRACT_ADDRESS,
      token: WETH_TOKEN_ADDRESS,
    });
  });
  test("parses WETH Transfer Event as null", () => {
    const address = "0x0000000000000000000000000000000000000001";
    const transferLog = {
      address: WETH_TOKEN_ADDRESS,
      topics: [
        TRANSFER_EVENT_TOPIC,
        addressToTopic(address),
        addressToTopic(SETTLEMENT_CONTRACT_ADDRESS),
      ],
      data: "0x0000000000000000000000000000000000000000000000000000000000001000",
    };
    const transferEvent = tryParseWethAction(transferLog);
    expect(transferEvent).toBeNull();
  });
  test("parses WETH Approval Event as null", () => {
    const address = "0x0000000000000000000000000000000000000001";
    const approvalLog = {
      address: WETH_TOKEN_ADDRESS,
      topics: [
        "0x8c5be1e5ebec7d5bd14f71427d1e84f3dd0314c0f7b2291e5b200ac8c7c3b925",
        addressToTopic(address),
        addressToTopic(SETTLEMENT_CONTRACT_ADDRESS),
      ],
      data: "0x000000000000000000000000000000000000000000000000016345785d8a0000",
    };
    const nullEvent = tryParseWethAction(approvalLog);
    expect(nullEvent).toBeNull();
  });
  test("parses Fake Deposit/Withdraw Events null", () => {
    const fakeDeposit = {
      address: ethers.ZeroAddress, // Not WETH!
      topics: [
        ETH_WRAP_EVENT_TOPIC,
        addressToTopic(SETTLEMENT_CONTRACT_ADDRESS),
      ],
      data: "0x00000000000000000000000000000000000000000000000000354a6ba7a18000",
    };
    expect(tryParseWethAction(fakeDeposit)).toBeNull();

    const fakeWithdrawal = {
      address: ethers.ZeroAddress, // Not WETH!
      topics: [
        ETH_UNWRAP_EVENT_TOPIC,
        addressToTopic(SETTLEMENT_CONTRACT_ADDRESS),
      ],
      data: "0x00000000000000000000000000000000000000000000000000354a6ba7a18000",
    };
    expect(tryParseWethAction(fakeWithdrawal)).toBeNull();
  });
});
