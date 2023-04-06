import { EventLog } from "../models";

/**
 *  Represents the relevant data returned from a transaction-simulation.
 */
export interface SimulationData {
  // # Transaction hash that would have been assigned if this were an actually mined tx.
  txHash: string;
  // Block on which the simulation was made.
  blockNumber: number;
  // Event Logs emitted within the transaction's simulation.
  logs: EventLog[];
}
