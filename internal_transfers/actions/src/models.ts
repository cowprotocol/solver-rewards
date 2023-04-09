// Event data declared here consists of only the relevant fields
// for our purposes at this time.
// For example, this program only requires the owner of the trade so
// that transfers can be classified AMM_{IN/OUT} or USER_{IN/OUT}.

export interface EventLog {
  // The contract address emitting the event
  address: string;
  // The indexed topics from the event log
  topics: string[];
  // The additional (non-indexed event data)
  data: string;
}

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

export interface WinningSettlementData {
  // Block at which settlement was simulated.
  simulationBlock: number;
  // Solver who submitted the (winning) solution
  solver: string;
  // Settlement call data: after internalized interactions have been removed.
  // equivalent to what actually appears on-chain.
  reducedCallData: string;
  // Full Call Data provided by the solver
  // null indicates that settlement was not pruned.
  fullCallData?: string;
}
