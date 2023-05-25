import {
  ethDeltaFromTraces,
  getTxDataFromHash,
  transferInvolves,
  validateDate
} from "../src/utils";
import { TransferEvent } from "../src/models";
import { ethers } from "ethers";
import { tryParseSettlementEventLog } from "../src/parse";
describe("transferInvolves(transfer, address)", () => {
  test("correctly returns whether transfer instance involves given address", () => {
    const address1 = "0x0000000000000000000000000000000000000001";
    const address2 = "0x0000000000000000000000000000000000000002";
    const address3 = "0x0000000000000000000000000000000000000003";
    const transfer: TransferEvent = {
      token: "Hello!",
      to: address1,
      from: address2,
      amount: BigInt(1),
    };
    expect(transferInvolves(transfer, address1)).toBe(true);
    expect(transferInvolves(transfer, address2)).toBe(true);
    expect(transferInvolves(transfer, address3)).toBe(false);
  });
});

describe("getTxDataFromHash(hash)", () => {
  test("does its job on basic transaction WETH unwrap", async () => {
    const provider = ethers.getDefaultProvider(
      process.env["NODE_URL"] || "NODE_URL"
    );

    expect(
      await getTxDataFromHash(
        provider,
        "0x2e8e115281bacc9753a31298bc9ef022eeb0f68d4c4762d4b50b757c0665b447"
      )
    ).toEqual({
      blockNumber: 17233653,
      from: "0xf1E13D28d19F5348A20E46fAC8E36791ca63Aa81",
      hash: "0x2e8e115281bacc9753a31298bc9ef022eeb0f68d4c4762d4b50b757c0665b447",
      logs: [
        {
          address: "0xC02aaA39b223FE8D0A0e5C4F27eAD9083C756Cc2",
          data: "0x00000000000000000000000000000000000000000000000000cd620a04977a9b",
          index: 305,
          topics: [
            "0x7fcf532c15f0a6db0bd6d0e038bea71d30d808c7d98cb3bf7268a95bf5081b65",
            "0x000000000000000000000000f1e13d28d19f5348a20e46fac8e36791ca63aa81",
          ],
        },
      ],
    });
  });
  test("Puts correct index on SettlementEvent logs", async () => {
    const provider = ethers.getDefaultProvider(
      process.env["NODE_URL"] || "NODE_URL"
    );

    const txData1 = await getTxDataFromHash(
      provider,
      "0xe08fd9651626cc0827a83721e9b6ef99a8be752d2a88490218f75ba84082a887"
    );
    expect(tryParseSettlementEventLog(txData1.logs.pop()!)).toEqual({
      logIndex: 104,
      solver: "0x0a308697e1d3a91dcB1e915C51F8944AaEc9015F",
    });

    const txData2 = await getTxDataFromHash(
      provider,
      "0xec894e53627f4b0a05be069a6c0c0cca08efe67f0b12deb85aeaa146f77eb049"
    );
    expect(tryParseSettlementEventLog(txData2.logs.pop()!)).toEqual({
      logIndex: 227,
      solver: "0x398890BE7c4FAC5d766E1AEFFde44B2EE99F38EF",
    });
  });
});

describe("ethDeltaFromTraces(transfer, address)", () => {
  test("computes ethDelta from real transaction traces", () => {
    // Non-Zero Traces from: 0xd51ed193555e780f09c54ffcca0d93821a8ec5ce18df4ace8cd6ff2b6e2f4da7
    const trace = [
      {
        callType: "CALL",
        from: "0xc02aaa39b223fe8d0a0e5c4f27ead9083c756cc2",
        to: "0x9008d19f58aabd9ed0d60971565aa8510560ab41",
        value: "0x2ba14232b75d7c4a0",
      },
      {
        callType: "CALL",
        from: "0x9008d19f58aabd9ed0d60971565aa8510560ab41",
        to: "0xd13c2691e0715efc6070f48242bf4317c84884f1",
        value: "0x4563918244f40000",
      },
      {
        callType: "CALL",
        from: "0x9008d19f58aabd9ed0d60971565aa8510560ab41",
        to: "0xb5d26158102181dc4ceee75f260a60debd752e45",
        value: "0x1f7f7ca4e4f971b44",
      },
      {
        callType: "CALL",
        from: "0x9008d19f58aabd9ed0d60971565aa8510560ab41",
        to: "0x11ebee2bf244325b5559f0f583722d35659ddce8",
        value: "0xa688906bd8b0000",
      },
      {
        callType: "CALL",
        from: "0x9008d19f58aabd9ed0d60971565aa8510560ab41",
        to: "0xc225c612926ef5f9e9578b865275a02bec6999ee",
        value: "0x568ed0ecd4f9a95c",
      },
      {
        callType: "CALL",
        from: "0x9008d19f58aabd9ed0d60971565aa8510560ab41",
        to: "0x3ea58745320b3ff174474841058903777573eea7",
        value: "0x1bc16d674ec80000",
      },
    ];
    expect(ethDeltaFromTraces(trace)).toEqual(
      new Map([
        ["0x9008d19f58aabd9ed0d60971565aa8510560ab41", 0n],
        ["0xc02aaa39b223fe8d0a0e5c4f27ead9083c756cc2", -50301868807575553184n],
        ["0xd13c2691e0715efc6070f48242bf4317c84884f1", 5000000000000000000n],
        ["0xb5d26158102181dc4ceee75f260a60debd752e45", 36314716558016846660n],
        ["0x11ebee2bf244325b5559f0f583722d35659ddce8", 750000000000000000n],
        ["0xc225c612926ef5f9e9578b865275a02bec6999ee", 6237152249558706524n],
        ["0x3ea58745320b3ff174474841058903777573eea7", 2000000000000000000n],
      ])
    );
  });
  test("computes ethDelta on basic, but comprehensive, example", () => {
    const trace = [
      {
        callType: "CALL",
        from: "0x1",
        to: "0x2",
        value: "0x1",
      },
      {
        callType: "CALL",
        from: "0x2",
        to: "0x3",
        value: "0x2",
      },
      {
        callType: "CALL",
        from: "0x4",
        to: "0x5",
        value: "0x0",
      },
    ];
    expect(ethDeltaFromTraces(trace)).toEqual(
      new Map([
        ["0x1", -1n],
        ["0x2", -1n],
        ["0x3", 2n],
      ])
    );
  });
});

describe('validateDate', () => {
  it('should return the valid date string', () => {
    const validDate = '2023-05-24';
    expect(validateDate(validDate)).toBe(validDate);
  });

  it('should throw an error for an invalid date format', () => {
    const invalidDate = '05/24/2023';
    expect(() => validateDate(invalidDate)).toThrow(
      'Invalid date format. Please use the YYYY-MM-DD format.'
    );
  });

  it('should throw an error for an empty string', () => {
    const emptyDate = '';
    expect(() => validateDate(emptyDate)).toThrow(
      'Invalid date format. Please use the YYYY-MM-DD format.'
    );
  });
});