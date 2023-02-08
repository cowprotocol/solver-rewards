export interface TradeEvent {
  // The only relevant field for our purposes at this time.
  owner: string;
}
export interface TransferEvent {
  to: string;
  from: string;
  amount: BigInt;
}

export interface SettlementEvent {
  solver: string;
}
