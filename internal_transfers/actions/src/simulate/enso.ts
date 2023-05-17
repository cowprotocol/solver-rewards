// EnsoFinance made a transaction simulator which can be found and run here:
// https://github.com/EnsoFinance/transaction-simulator
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
        gasLimit: 5000000,
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
    if (!isEnsoSimulationResponse(response.data)) {
      throw Error(`Invalid Response ${JSON.stringify(response.data)}`);
    }
    return parseEnsoSimulation(response.data);
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

export function isEnsoSimulationResponse(
  value: any
): value is EnsoSimulationResponse {
  if (!value || typeof value !== "object") return false;
  const { simulationId, gasUsed, blockNumber, success, trace, logs } = value;
  if (!simulationId || typeof simulationId !== "number") return false;
  if (!gasUsed || typeof gasUsed !== "number") return false;
  if (!blockNumber || typeof blockNumber !== "number") return false;
  if (!success || typeof success !== "boolean") return false;
  return Array.isArray(logs) && Array.isArray(trace);
  // Even more could be done here (like 0x prefixed strings, etc...)
  // or logs & traces are actually logs and traces.
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
  throw Error(`Invalid simulation data ${JSON.stringify(simulation)}`);
}
