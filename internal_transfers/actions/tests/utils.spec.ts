import { getTxDataFromHash, transferInvolves } from "../src/utils";
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
