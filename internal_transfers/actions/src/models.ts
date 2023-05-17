// Event data declared here consists of only the relevant fields
// for our purposes at this time.
// For example, this program only requires the owner of the trade so
// that transfers can be classified AMM_{IN/OUT} or USER_{IN/OUT}.

export interface TokenImbalance {
  token: string;
  amount: bigint;
}

export interface EventLog {
  // Block-wise index of Log
  readonly index: number;
  // The contract address emitting the event
  readonly address: string;
  // The indexed topics from the event log
  readonly topics: string[];
  // The additional (non-indexed event data)
  readonly data: string;
}

export interface TradeEvent {
  owner: string;
}

export function isTradeEvent(event: any): event is TradeEvent {
  const castEvent = event as TradeEvent;
  return castEvent.owner !== undefined;
}
export interface TransferEvent {
  token: string;
  to: string;
  from: string;
  amount: bigint;
}
export interface EventMeta {
  blockNumber: number;
  txHash: string;
}

export interface SettlementEvent {
  solver: string;
  logIndex: number;
}

export function isSettlementEvent(event: any): event is SettlementEvent {
  const castEvent = event as SettlementEvent;
  return castEvent.solver !== undefined && castEvent.logIndex !== undefined;
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
