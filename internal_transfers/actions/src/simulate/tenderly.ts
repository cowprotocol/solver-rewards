import axios from "axios";
import {
  SimulationData,
  SimulationParams,
  TransactionSimulator,
} from "./interface";
import { EventLog } from "../models";

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
        gas: 5000000,
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
}

interface TenderlyTransaction {
  transaction_info: TenderlyTransactionInfo;
  hash: string;
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
  raw: EventLog;
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
  return (
    Array.isArray(logs) && (logs.length === 0 || logs[0].raw !== undefined)
  );
  // Even more could be done here (like 0x prefixed strings, etc...)
}
export function parseTenderlySimulation(
  simulation: TenderlySimulationResponse
): SimulationData {
  const { transaction: tx } = simulation;
  if (tx != undefined) {
    return {
      blockNumber: tx.transaction_info.block_number,
      txHash: tx.hash,
      logs: tx.transaction_info.logs.map((t: { raw: EventLog }) => t.raw) || [],
      ethDelta: new Map(
        tx.transaction_info.balance_diff.map((t) => [
          t.address.toLowerCase(),
          BigInt(t.dirty - t.original),
        ])
      ),
    };
  }
  throw Error(`Invalid simulation data ${JSON.stringify(simulation)}`);
}
