import { SETTLEMENT_CONTRACT_ADDRESS } from "./constants";
import { getSettlementCompetitionData } from "./orderbook";
import { SimulationData, TransactionSimulator } from "./simulate/interface";
import { partitionEventLogs } from "./parse";
import { TokenImbalance, WinningSettlementData, EventLog } from "./models";
import {
  aggregateTransfers,
  ImbalanceMap,
  imbalanceMapDiff,
} from "./imbalance";

const ETH_TOKEN = "0xeeeeeeeeeeeeeeeeeeeeeeeeeeeeeeeeeeeeeeee";

// This represents the only required fields for InternalImbalance accounting
// An object of this shape can be easily be constructed from any of
// - ethers - `TransactionReceipt`,
// - tenderly - `TransactionEvent`
export interface MinimalTxData {
  readonly blockNumber: number;
  readonly from: string;
  readonly hash: string;
  readonly logs: EventLog[];
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

export interface SettlementSimulationData {
  txHash: string;
  winningSettlement: WinningSettlementData;
  full: SimulationData;
  reduced: SimulationData;
}

export async function simulateSolverSolution(
  transaction: MinimalTxData,
  simulator: TransactionSimulator
): Promise<SettlementSimulationData | null> {
  const solverAddress = transaction.from.toLowerCase();
  const competition = await getSettlementCompetitionData(transaction.hash);
  if (competition === undefined) {
    throw Error(`No competition found for ${transaction.hash}`);
  }

  if (competition.fullCallData === undefined) {
    // Settlement was not even partially internalized.
    // https://api.cow.fi/docs/#/default/get_api_v1_solver_competition_by_tx_hash__tx_hash_
    // No need to simulate!
    console.log(`batch ${transaction.hash} was not internalized.`);
    return null;
  }
  // Try all blocks between claimed simulation block and mined block.
  const numAttempts = transaction.blockNumber - competition.simulationBlock + 1;
  try {
    const { full, reduced } = await simulateBoth(
      simulator,
      {
        full: competition.fullCallData,
        reduced: competition.reducedCallData,
        common: {
          contractAddress: SETTLEMENT_CONTRACT_ADDRESS,
          sender: solverAddress,
          value: "0",
        },
        startBlock: competition.simulationBlock,
      },
      numAttempts
    );
    return {
      txHash: transaction.hash,
      winningSettlement: competition,
      full,
      reduced,
    };
  } catch (error: any) {
    console.error(error.message);
    // Sometimes (rarely) we can't simulate both components of the solver competition data.
    // When this happens, it is assumed that there were no internalized transfers
    // and write a kind of placeholder/trivial record as follows:
    const failedSimulation = {
      simulationID: `failed all ${numAttempts} simulation attempts`,
      blockNumber: -1, // easily identifiable "trivial simulation record"
      gasUsed: 0, // 0 will not affect aggregate sums on gas consumption (i.e. analytics)
      logs: [], // implies no token transfers.
      ethDelta: new Map(), // implies no eth balance diff.
    };
    return {
      txHash: transaction.hash,
      winningSettlement: competition,
      full: failedSimulation,
      reduced: failedSimulation,
    };
  }
}

interface commonSimulationParams {
  contractAddress: string;
  sender: string;
  value: string;
}

interface SettlementSimulationParams {
  full: string;
  reduced: string;
  common: commonSimulationParams;
  startBlock: number;
}

interface SimulationPair {
  full: SimulationData;
  reduced: SimulationData;
}

async function simulateBoth(
  simulator: TransactionSimulator,
  params: SettlementSimulationParams,
  numAttempts: number = 3
): Promise<SimulationPair> {
  let attemptNumber = 0;
  while (attemptNumber < numAttempts) {
    try {
      return {
        full: await simulator.simulate({
          ...params.common,
          blockNumber: params.startBlock + attemptNumber,
          callData: params.full,
        }),
        reduced: await simulator.simulate({
          ...params.common,
          blockNumber: params.startBlock + attemptNumber,
          callData: params.reduced,
        }),
      };
    } catch (error) {
      attemptNumber += 1;
      console.warn(`Failed simulation attempt ${attemptNumber}`);
    }
  }
  throw new Error(
    `failed simulations on ${numAttempts} blocks beginning from ${params.startBlock}`
  );
}

export function getInternalizedImbalance(
  simulationData: SettlementSimulationData
): TokenImbalance[] {
  const fullSimulationImbalance = constructImbalanceMap(
    simulationData.full,
    SETTLEMENT_CONTRACT_ADDRESS
  );
  const reducedSimulationImbalance = constructImbalanceMap(
    simulationData.reduced,
    SETTLEMENT_CONTRACT_ADDRESS
  );

  return imbalanceMapDiff(fullSimulationImbalance, reducedSimulationImbalance);
}
