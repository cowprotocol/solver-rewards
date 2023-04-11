import { imbalanceMapDiff } from "../src/imbalance";

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
