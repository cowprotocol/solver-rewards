// Event data declared here consists of only the relevant fields
// for our purposes at this time.
// For example, this program only requires the owner of the trade so
// that transfers can be classified AMM_{IN/OUT} or USER_{IN/OUT}.
export interface TradeEvent {
  owner: string;
}
export interface TransferEvent {
  to: string;
  from: string;
  amount: BigInt;
}
export interface EventMeta {
  blockNumber: number;
  txHash: string;
}

export interface SettlementEvent {
  solver: string;
  logIndex: number;
}
