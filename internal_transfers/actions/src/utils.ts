import { TransferEvent } from "./models";

export function addressFromBytes32(hexStr: string): string {
  return "0x" + hexStr.slice(-40);
}

export function transferInvolves(
  transfer: TransferEvent,
  address: string
): boolean {
  return [transfer.to.toLowerCase(), transfer.from.toLowerCase()].includes(
    address.toLowerCase()
  );
}
