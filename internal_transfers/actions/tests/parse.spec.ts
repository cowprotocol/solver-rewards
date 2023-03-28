import { partitionEventLogs } from "../src/parse";
import { address as SETTLEMENT_CONTRACT_ADDRESS } from "@cowprotocol/contracts/deployments/mainnet/GPv2Settlement.json";

const SETTLEMENT_EVENT_TOPIC =
  "0x40338ce1a7c49204f0099533b1e9a7ee0a3d261f84974ab7af36105b8c4e9db4";
const TRANSFER_EVENT_TOPIC =
  "0xddf252ad1be2c89b69c2b068fc378daa952ba7f163c4a11628f55a4df523b3ef";
const TRADE_EVENT_TOPIC =
  "0xa07a543ab8a018198e99ca0184c93fe9050a79400a0a723441f84de1d972cc17";

const TOKEN_ADDRESS = "0xc02aaa39b223fe8d0a0e5c4f27ead9083c756cc2";

function addressToTopic(address: string): string {
  return "0x000000000000000000000000" + address.slice(2);
}
describe("partitionEventLogs(logs)", () => {
  test("single Trade Event", () => {
    const tradeOwner = "0xd5553C9726EA28e7EbEDfe9879cF8aB4d061dbf0";
    const tradeLog = {
      address: SETTLEMENT_CONTRACT_ADDRESS,
      data: "0x0000000000000000000000006b175474e89094c44da98b954eedeac495271d0f0000000000000000000000003432b6a60d23ca0dfca7761b7ab56459d9c964d000000000000000000000000000000000000000000000006c6b935b8bbd400000000000000000000000000000000000000000000000000019753399721b8078ee000000000000000000000000000000000000000000000000604fbfc634eef00000000000000000000000000000000000000000000000000000000000000000c00000000000000000000000000000000000000000000000000000000000000038bf293f652b46fe85a15838d7ff736add1b6098ed1c143f3902869d325f9e0069e2b424053b9ebfcedf89ecb8bf2972974e98700c63af639e0000000000000000",
      topics: [TRADE_EVENT_TOPIC, addressToTopic(tradeOwner)],
    };
    const { trades, transfers, settlements } = partitionEventLogs([tradeLog]);

    expect(trades).toStrictEqual([{ owner: tradeOwner }]);
    expect(transfers).toStrictEqual([]);
    expect(settlements).toStrictEqual([]);
  });
  test("single relevant Transfer Event", () => {
    const address = "0x0000000000000000000000000000000000000001";
    const relevant_transfer_log = {
      address: TOKEN_ADDRESS,
      topics: [
        TRANSFER_EVENT_TOPIC,
        addressToTopic(address),
        addressToTopic(SETTLEMENT_CONTRACT_ADDRESS),
      ],
      data: "0x0000000000000000000000000000000000000000000000000000000000001000",
    };
    const irrelevant_transfer_log = {
      address: TOKEN_ADDRESS,
      topics: [
        TRANSFER_EVENT_TOPIC,
        "0x0000000000000000000000000000000000000000000000000000000000000001",
        "0x0000000000000000000000000000000000000000000000000000000000000002",
      ],
      data: "0x000000000000000000000000000000000000000000000000000000000000000f",
    };
    const { trades, transfers, settlements } = partitionEventLogs([
      relevant_transfer_log,
      irrelevant_transfer_log,
    ]);

    expect(trades).toStrictEqual([]);
    expect(transfers.length).toBe(1);
    expect(transfers[0].to).toStrictEqual(SETTLEMENT_CONTRACT_ADDRESS);
    expect(transfers[0].from).toStrictEqual(address);
    expect(transfers[0].amount.toString()).toBe(BigInt(4096).toString());
    expect(settlements).toStrictEqual([]);
  });
  test("single Settlement Event", () => {
    const solverAddress = "0xb20B86C4e6DEEB432A22D773a221898bBBD03036";
    const settlement_log = {
      address: SETTLEMENT_CONTRACT_ADDRESS,
      topics: [SETTLEMENT_EVENT_TOPIC, addressToTopic(solverAddress)],
      data: "0x",
    };
    const { trades, transfers, settlements } = partitionEventLogs([
      settlement_log,
    ]);

    expect(trades).toStrictEqual([]);
    expect(transfers).toStrictEqual([]);
    expect(settlements).toStrictEqual([
      { solver: solverAddress, log_index: 0 },
    ]);
  });
  test("no relevant events", () => {
    const irrelevant_event_log = {
      address: "0xc02aaa39b223fe8d0a0e5c4f27ead9083c756cc2",
      topics: [
        "0x7fcf532c15f0a6db0bd6d0e038bea71d30d808c7d98cb3bf7268a95bf5081b65",
        "0x0000000000000000000000009008d19f58aabd9ed0d60971565aa8510560ab41",
      ],
      data: "0x",
    };
    const { trades, transfers, settlements } = partitionEventLogs([
      irrelevant_event_log,
    ]);

    expect(trades).toStrictEqual([]);
    expect(transfers).toStrictEqual([]);
    expect(settlements).toStrictEqual([]);
  });
});
