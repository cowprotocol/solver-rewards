import { aggregateTransfers, imbalanceMapDiff } from "../src/imbalance";
import { TransferEvent } from "../src/models";
import { address as SETTLEMENT_CONTRACT_ADDRESS } from "@cowprotocol/contracts/deployments/mainnet/GPv2Settlement.json";

const TOKEN_ADDRESS = "0x-token!";
describe("aggregateTransfers(transfers, focalAccount)", () => {
  test("works in generic setting", () => {
    const address = "0x0000000000000000000000000000000000000001";
    const transferEvents: TransferEvent[] = [
      // Incoming
      {
        amount: BigInt("100"),
        from: address,
        to: SETTLEMENT_CONTRACT_ADDRESS,
        token: TOKEN_ADDRESS,
      },
      // Outgoing
      {
        amount: BigInt("200"),
        from: SETTLEMENT_CONTRACT_ADDRESS,
        to: address,
        token: TOKEN_ADDRESS,
      },
      // Irrelevant
      {
        amount: BigInt("300"),
        from: address,
        to: address,
        token: TOKEN_ADDRESS,
      },
    ];

    expect(
      aggregateTransfers(transferEvents, SETTLEMENT_CONTRACT_ADDRESS)
    ).toEqual(new Map([[TOKEN_ADDRESS, BigInt("-100")]]));
  });
});
describe("imbalanceMapDiff(mapA, mapB)", () => {
  test("map difference returns expected values in generic setting", () => {
    const mapA = new Map([
      ["a", 1n],
      ["b", 2n],
    ]);
    const mapB = new Map([
      ["b", 3n],
      ["c", 4n],
    ]);

    expect(imbalanceMapDiff(mapA, mapB)).toEqual([
      {
        amount: 1n,
        token: "a",
      },
      {
        amount: -1n,
        token: "b",
      },
      {
        amount: -4n,
        token: "c",
      },
    ]);

    expect(imbalanceMapDiff(new Map(), new Map())).toEqual([]);
  });

  test("map difference returns expected values on empty", () => {
    expect(imbalanceMapDiff(new Map(), new Map())).toEqual([]);
    const testMap = new Map([["x", 1n]]);
    expect(imbalanceMapDiff(testMap, new Map())).toEqual([
      {
        amount: 1n,
        token: "x",
      },
    ]);
    expect(imbalanceMapDiff(new Map(), testMap)).toEqual([
      {
        amount: -1n,
        token: "x",
      },
    ]);
  });
});
