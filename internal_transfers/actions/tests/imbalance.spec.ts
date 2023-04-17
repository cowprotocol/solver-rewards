import { aggregateTransfers, imbalanceMapDiff } from "../src/imbalance";
import { TransferEvent } from "../src/models";

describe("aggregateTransfers(transfers, focalAccount)", () => {
  test("works in generic setting", () => {
    const tokenAddress = "0x-token";
    const focalAddress = "0x-focal";
    const irrelevantAddress = "0x-irrelevant";

    const transferEvents: TransferEvent[] = [
      // Incoming
      {
        amount: BigInt("100"),
        from: irrelevantAddress,
        to: focalAddress,
        token: tokenAddress,
      },
      // Outgoing
      {
        amount: BigInt("200"),
        from: focalAddress,
        to: irrelevantAddress,
        token: tokenAddress,
      },
      // Irrelevant
      {
        amount: BigInt("300"),
        from: irrelevantAddress,
        to: irrelevantAddress,
        token: tokenAddress,
      },
    ];

    expect(aggregateTransfers(transferEvents, focalAddress)).toEqual(
      new Map([[tokenAddress, BigInt("-100")]])
    );
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

  test("map difference excludes zeros", () => {
    const testMap = new Map([["x", 1n]]);
    expect(imbalanceMapDiff(testMap, testMap)).toEqual([]);
  });
});
