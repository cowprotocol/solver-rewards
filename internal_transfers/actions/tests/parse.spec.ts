import {
  partitionEventLogs,
  SETTLEMENT_CONTRACT_ADDRESS,
  SETTLEMENT_EVENT_TOPIC,
  TRADE_EVENT_TOPIC,
  TRANSFER_EVENT_TOPIC,
} from "../src/parse";

const TOKEN_ADDRESS = "0xc02aaa39b223fe8d0a0e5c4f27ead9083c756cc2";
describe("partitionEventLogs(logs)", () => {
  test("partitions event logs single Trade Event", () => {
    const tradeOwner = "0xd5553c9726ea28e7ebedfe9879cf8ab4d061dbf0";
    const trade_log = {
      address: SETTLEMENT_CONTRACT_ADDRESS,
      topics: [TRADE_EVENT_TOPIC, "0x000000000000000000000000" + tradeOwner],
      data: "0x",
    };
    const { trades, transfers, settlements } = partitionEventLogs([trade_log]);

    expect(trades).toStrictEqual([{ owner: tradeOwner }]);
    expect(transfers).toStrictEqual([]);
    expect(settlements).toStrictEqual([]);
  });

  test("partitions event logs single relevant Transfer Event", () => {
    const address = "0x0000000000000000000000000000000000000001";
    const relevant_transfer_log = {
      address: TOKEN_ADDRESS,
      topics: [
        TRANSFER_EVENT_TOPIC,
        "0x000000000000000000000000" + address,
        "0x000000000000000000000000" + SETTLEMENT_CONTRACT_ADDRESS,
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
  test("partitions event logs with single Settlement Event", () => {
    const solverAddress = "0xb20b86c4e6deeb432a22d773a221898bbbd03036";
    const settlement_log = {
      address: SETTLEMENT_CONTRACT_ADDRESS,
      topics: [
        SETTLEMENT_EVENT_TOPIC,
        "0x000000000000000000000000" + solverAddress,
      ],
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

  test("partitions event logs with no relevant events", () => {
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
