import { aggregateTransfers, transferInvolves } from "../src/utils";
import { TransferEvent } from "../src/models";
import { address as SETTLEMENT_CONTRACT_ADDRESS } from "@cowprotocol/contracts/deployments/mainnet/GPv2Settlement.json";

const TOKEN_ADDRESS = "SuperToken!";
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
