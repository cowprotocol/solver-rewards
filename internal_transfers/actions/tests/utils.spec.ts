import { addressFromBytes32, transferInvolves } from "../src/utils";
import { TransferEvent } from "../src/models";

describe("addressFromBytes32(hexStr)", () => {
  test("parses address from event topic hex string", () => {
    const addressTopic =
      "0x0000000000000000000000009008d19f58aabd9ed0d60971565aa8510560ab41";
    expect(addressFromBytes32(addressTopic)).toBe(
      "0x9008d19f58aabd9ed0d60971565aa8510560ab41"
    );
  });
});

describe("transferInvolves(transfer, address)", () => {
  test("correctly returns whether transfer instance involves given address", () => {
    const address1 = "0x0000000000000000000000000000000000000001";
    const address2 = "0x0000000000000000000000000000000000000002";
    const address3 = "0x0000000000000000000000000000000000000003";
    const transfer: TransferEvent = {
      to: address1,
      from: address2,
      amount: BigInt(1),
    };
    expect(transferInvolves(transfer, address1)).toBe(true);
    expect(transferInvolves(transfer, address2)).toBe(true);
    expect(transferInvolves(transfer, address3)).toBe(false);
  });
});
