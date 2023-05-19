// PhalconFinance made a transaction simulator which can be found and run here:
// https://github.com/PhalconFinance/transaction-simulator
// One can follow the instructions there to run a simulation API.
import axios from "axios";
import {
  SimulationData,
  SimulationParams,
  TransactionSimulator,
} from "./interface";
import { Log } from "@tenderly/actions";
import { Trace } from "../models";
import { ethDeltaFromTraces } from "../utils";

export class PhalconSimulator implements TransactionSimulator {
  url: string;

  constructor(url: string) {
    this.url = url;
  }

  async simulate(params: SimulationParams): Promise<SimulationData> {
    const {
      sender,
      contractAddress,
      callData,
      blockNumber,
      value = "0",
    } = params;
    const response = await axios.post(
      "https://explorer.phalcon.xyz/api/v1/tx/simulate/2",
      {
        chainID: 1,
        sender,
        receiver: contractAddress,
        inputData: callData,
        value,
        block: blockNumber,
        position: 0,
        gasLimit: 10000000,
        gasPrice: "100",
      },
      {
        headers: {
          "Content-Type": "application/json",
        },
      }
    );
    if (!isPhalconSimulationResponse(response.data)) {
      throw Error(`Invalid Response ${JSON.stringify(response.data)}`);
    }
    return parsePhalconSimulation(response.data);
  }
}

interface PhalconSimulationResponse {
  latestBlock: number;
  transaction: PhalconTransaction
}

interface PhalconTransaction {
  accountLabels: AccountLabel[];
  balanceChanges: BalanceChange[]
}

interface AccountLabel {
  address: string;
  label: string;
}

interface BalanceChange {
  account: string;
  assets:
}
export function isPhalconSimulationResponse(
  value: any
): value is PhalconSimulationResponse {
  console.log(value);
  return true;
}
export function parsePhalconSimulation(
  simulation: PhalconSimulationResponse
): SimulationData {
  if (simulation.success) {
    return {
      simulationID: `Phalcon-${simulation.simulationId}`,
      blockNumber: simulation.blockNumber,
      gasUsed: simulation.gasUsed,
      logs:
        simulation.logs.map((t: Log, index) => ({
          ...t,
          index,
        })) || [],
      ethDelta: ethDeltaFromTraces(simulation.trace),
    };
  }
  throw Error(`Invalid simulation data ${JSON.stringify(simulation)}`);
}
