import { EventLog } from "../models";

export const SIMULATION_GAS_LIMIT = 10e6;
export interface SimulationParams {
  // Ethereum address transaction should be sent to.
  contractAddress: string;
  // Ethereum address of transaction sender.
  sender: string;
  // 0x-prefixed string representing transaction data to simulate.
  callData: string;
  // Amount of Ether to send along with transaction.
  value: string;
  // Block at which simulation should be made.
  // use "latest" when undefined.
  blockNumber?: number;
}

/**
 *  Represents the relevant data returned from a transaction-simulation.
 */
export interface SimulationData {
  // Some identifier of the simulation (e.g. a URL)
  simulationID: string;
  // Block on which the simulation was made.
  blockNumber: number;
  // Gas used by transaction
  gasUsed: number;
  // Event Logs emitted within the transaction's simulation.
  logs: EventLog[];
  // Difference in ETH balances of all accounts in transaction
  ethDelta: Map<string, bigint>;
}

export interface TransactionSimulator {
  /**
   * Simulates the given `callData` uses whatever means of EVM transaction simulation at `block_number`.
   * Returns sufficiently relevant parts of the simulation to build Settlement Transfers.
   * Simulation request would correspond to the following transaction data:
   * {
   *      "to": contractAddress,
   *      "from": sender,
   *      "data": callData
   *      "value": 0,
   * }
   *
   * @param transactionData - Elementary Transaction Data
   * @returns Relevant content from Simulation Results.
   */
  simulate(transactionData: SimulationParams): Promise<SimulationData>;
}
