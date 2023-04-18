import { address as SETTLEMENT_CONTRACT_ADDRESS } from "@cowprotocol/contracts/deployments/mainnet/GPv2Settlement.json";
import { getSettlementCompetitionData } from "./orderbook";
import { SimulationData, TransactionSimulator } from "./simulate/interface";
import assert from "assert";
import { partitionEventLogs } from "./parse";
import { Log } from "@tenderly/actions";
import { TokenImbalance } from "./models";
import {
  aggregateTransfers,
  ImbalanceMap,
  imbalanceMapDiff,
} from "./imbalance";
import { ZeroAddress } from "ethers";

const ETH_TOKEN = "0xeeeeeeeeeeeeeeeeeeeeeeeeeeeeeeeeeeeeeeee";

// This represents the only required fields for InternalImbalance accounting
// An object of this shape can be easily be constructed from any of
// - ethers - `TransactionReceipt`,
// - tenderly - `TransactionEvent`
export interface MinimalTxData {
  readonly from: string;
  readonly hash: string;
  readonly logs: Log[];
}

export function constructImbalanceMap(
  simulation: SimulationData,
  focalContract: string
): ImbalanceMap {
  focalContract = focalContract.toLowerCase();
  const { transfers } = partitionEventLogs(simulation.logs);

  const simulationImbalance = aggregateTransfers(transfers, focalContract);
  const ethImbalance = simulation.ethDelta.get(focalContract) ?? 0n;
  if (ethImbalance !== 0n) {
    simulationImbalance.set(ETH_TOKEN, ethImbalance);
  }

  return simulationImbalance;
}

export async function getInternalizedImbalance(
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
    solverAddress === competition.solver || competition.solver === ZeroAddress,
    `Winning solver ${competition.solver} doesn't match settlement solver ${solverAddress}`
  );
  if (competition.fullCallData === undefined) {
    // Settlement was not even partially internalized.
    // https://api.cow.fi/docs/#/default/get_api_v1_solver_competition_by_tx_hash__tx_hash_
    // No need to simulate!
    console.log(`Batch ${transaction.hash} not internalized.`);
    return [];
  }

  const commonSimulationParams = {
    contractAddress: SETTLEMENT_CONTRACT_ADDRESS,
    sender: solverAddress,
    value: "0",
    blockNumber: competition.simulationBlock,
  };
  const simFull = await simulator.simulate({
    ...commonSimulationParams,
    callData: competition.fullCallData,
  });
  const simReduced = await simulator.simulate({
    ...commonSimulationParams,
    callData: competition.reducedCallData,
  });

  const fullSimulationImbalance = constructImbalanceMap(
    simFull,
    SETTLEMENT_CONTRACT_ADDRESS
  );
  const reducedSimulationImbalance = constructImbalanceMap(
    simReduced,
    SETTLEMENT_CONTRACT_ADDRESS
  );

  return imbalanceMapDiff(fullSimulationImbalance, reducedSimulationImbalance);
}
