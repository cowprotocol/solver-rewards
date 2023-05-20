// EnsoFinance made a transaction simulator which can be found and run here:
// https://github.com/EnsoFinance/transaction-simulator
// One can follow the instructions there to run a simulation API.
import axios from "axios";
import {
  SIMULATION_GAS_LIMIT,
  SimulationData,
  SimulationParams,
  TransactionSimulator,
} from "./interface";
import { Log } from "@tenderly/actions";
import { Trace } from "../models";
import { ethDeltaFromTraces } from "../utils";

export class EnsoSimulator implements TransactionSimulator {
  url: string;
  accessKey?: string;

  constructor(url: string, accessKey?: string) {
    this.url = url;
    this.accessKey = accessKey;
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
      this.url,
      {
        chainId: 1,
        from: sender,
        to: contractAddress,
        data: callData,
        gasLimit: SIMULATION_GAS_LIMIT,
        blockNumber,
        value,
      },
      {
        headers: {
          "X-API-KEY": this.accessKey,
          "Content-Type": "application/json",
        },
      }
    );
    if (response.status != 200) {
      throw Error(
        `Invalid Response with status ${response.status} - ${JSON.stringify(
          response
        )}`
      );
    }
    return parseEnsoSimulation(response.data as EnsoSimulationResponse);
  }
}

interface EnsoSimulationResponse {
  simulationId: string;
  gasUsed: number;
  blockNumber: number;
  success: boolean;
  trace: Trace[];
  logs: Log[];
}
export function parseEnsoSimulation(
  simulation: EnsoSimulationResponse
): SimulationData {
  if (simulation.success) {
    return {
      simulationID: `enso-${simulation.simulationId}`,
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
  throw Error(`simulation failed ${JSON.stringify(simulation)}`);
}
