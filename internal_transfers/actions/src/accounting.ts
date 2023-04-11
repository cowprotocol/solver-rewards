import { address as SETTLEMENT_CONTRACT_ADDRESS } from "@cowprotocol/contracts/deployments/mainnet/GPv2Settlement.json";
import { getSettlementCompetitionData } from "./orderbook";
import { TransactionSimulator } from "./simulate/interface";
import assert from "assert";
import { partitionEventLogs } from "./parse";
import { Log } from "@tenderly/actions";
import { TokenImbalance } from "./models";
import { aggregateTransfers, imbalanceMapDiff } from "./imbalance";

// This represents the only required fields for InternalImbalance accounting
// An object of this shape can be easily be constructed from any of
// - ethers - `TransactionReceipt`,
// - tenderly - `TransactionEvent`
export interface MinimalTxData {
  readonly from: string;
  readonly hash: string;
  readonly logs: Log[];
}
export async function getInternalImbalance(
  transaction: MinimalTxData,
  simulator: TransactionSimulator
): Promise<TokenImbalance[]> {
  const solverAddress = transaction.from.toLowerCase();
  const competition = await getSettlementCompetitionData(transaction.hash);
  if (competition === undefined) {
    throw Error(`No competition found for ${transaction.hash}`);
  }

  // This is more of a monitoring system task!
  assert(
    solverAddress === competition.solver ||
      competition.solver === "0x0000000000000000000000000000000000000000",
    `Winning solver ${competition.solver} doesn't match settlement solver ${solverAddress}`
  );
  if (competition.fullCallData === undefined) {
    // Settlement was not even partially internalized. Return before simulating!
    return [];
  }
  const simulation = await simulator.simulate({
    callData: competition.fullCallData,
    contractAddress: SETTLEMENT_CONTRACT_ADDRESS,
    sender: solverAddress,
    value: "0",
    blockNumber: competition.simulationBlock + 1,
  });
  // TODO - figure out what happens when simulation fails and handle it!

  const { transfers: simTransfers } = partitionEventLogs(simulation.logs);
  const { transfers: actualTransfers } = partitionEventLogs(transaction.logs);

  console.log(
    `Found ${actualTransfers.length} relevant Actual Transfers and ${simTransfers.length} relevant Simulated Transfers`
  );

  const simulationImbalance = aggregateTransfers(
    simTransfers,
    SETTLEMENT_CONTRACT_ADDRESS
  );
  const actualImbalance = aggregateTransfers(
    actualTransfers,
    SETTLEMENT_CONTRACT_ADDRESS
  );

  return imbalanceMapDiff(simulationImbalance, actualImbalance);
}
