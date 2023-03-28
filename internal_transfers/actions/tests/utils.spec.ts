import { transferInvolves } from "../src/utils";
import { TransferEvent } from "../src/models";

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
