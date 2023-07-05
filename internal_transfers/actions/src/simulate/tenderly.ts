import axios from "axios";
import {
  SIMULATION_GAS_LIMIT,
  SimulationData,
  SimulationParams,
  TransactionSimulator,
} from "./interface";
import { Log } from "@tenderly/actions";

export class TenderlySimulator implements TransactionSimulator {
  BASE_URL = "https://api.tenderly.co/api";
  user: string;
  project: string;
  accessKey: string;

  constructor(user: string, project: string, accessKey: string) {
    this.user = user;
    this.project = project;
    this.accessKey = accessKey;
  }
  async simulate(params: SimulationParams): Promise<SimulationData> {
    const SIMULATE_URL = `${this.BASE_URL}/v1/account/${this.user}/project/${this.project}/simulate`;
    const {
      sender,
      contractAddress,
      callData,
      blockNumber,
      value = "0",
    } = params;
    const response = await axios.post(
      SIMULATE_URL,
      {
        network_id: "1",
        from: sender,
        to: contractAddress,
        input: callData,
        block_number: blockNumber,
        gas: SIMULATION_GAS_LIMIT,
        gas_price: "0",
        value,
        // simulation config (tenderly specific)
        // We have decided to always save simulations...
        // then we can store simulation IDs and refer back to them
        save_if_fails: true,
        save: true,
        simulation_type: "quick",
      },
      {
        headers: {
          "X-Access-Key": this.accessKey,
          "Content-Type": "application/json",
          Accept: "application/json",
        },
      }
    );
    if (!isTenderlySimulationResponse(response.data)) {
      throw Error(`Invalid Response ${JSON.stringify(response.data)}`);
    }
    return parseTenderlySimulation(response.data);
  }
}

interface TenderlySimulationResponse {
  transaction: TenderlyTransaction;
  simulation: TenderlySimulation;
}

interface TenderlyTransaction {
  transaction_info: TenderlyTransactionInfo;
  hash: string;
}
interface TenderlySimulation {
  id: string;
  gas_used: number;
}

interface TenderlyTransactionInfo {
  block_number: number;
  logs: TenderlyTransactionLog[];
  balance_diff: TenderlyBalanceDiff[];
}

interface TenderlyBalanceDiff {
  address: string;
  // before
  original: bigint;
  // after
  dirty: bigint;
}
interface TenderlyTransactionLog {
  raw: Log;
}

export function isTenderlySimulationResponse(
  value: any
): value is TenderlySimulationResponse {
  if (!value || typeof value !== "object") return false;
  if (value.transaction === undefined) return false;
  const tx = value.transaction;
  if (tx.transaction_info === undefined || typeof tx.hash !== "string")
    return false;
  const info = tx.transaction_info;
  if (typeof info.block_number !== "number" || info.logs === undefined)
    return false;
  const logs = info.logs;
  if (
    !(Array.isArray(logs) && (logs.length === 0 || logs[0].raw !== undefined))
  )
    return false;
  if (value.simulation === undefined) return false;
  const sim = value.simulation;
  return typeof sim.id === "string" && typeof sim.gas_used === "number";

  // Even more could be done here (like 0x prefixed strings, etc...)
}
export function parseTenderlySimulation(
  simulation: TenderlySimulationResponse
): SimulationData {
  const { transaction: tx } = simulation;
  if (tx != undefined) {
    const balanceDiff = tx.transaction_info.balance_diff ?? [];
    return {
      simulationID: `tenderly-${simulation.simulation.id}`,
      blockNumber: tx.transaction_info.block_number,
      gasUsed: simulation.simulation.gas_used,
      logs:
        tx.transaction_info.logs.map((t: { raw: Log }, index) => ({
          ...t.raw,
          index,
        })) || [],
      ethDelta: new Map(
        balanceDiff.map((t) => [
          t.address.toLowerCase(),
          BigInt(t.dirty - t.original),
        ])
      ),
    };
  }
  throw Error(`Invalid simulation data ${JSON.stringify(simulation)}`);
}
