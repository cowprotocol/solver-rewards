import {
  isSettlementEvent,
  isTradeEvent,
  SettlementEvent,
  TradeEvent,
  TransferEvent,
} from "./models";
import { Log } from "@tenderly/actions";
import { transferInvolves } from "./utils";
import { ethers } from "ethers";
import { abi as SETTLEMENT_ABI } from "./artifacts/GPv2Settlement.json";
import { abi as IERC20_ABI } from "./artifacts/IERC20.json";
import { abi as WETH9_ABI } from "./artifacts/weth9_abi.json";
import { SETTLEMENT_CONTRACT_ADDRESS } from "./constants";

export const WETH_TOKEN_ADDRESS = "0xc02aaa39b223fe8d0a0e5c4f27ead9083c756cc2";

const settlementInterface = new ethers.Interface(SETTLEMENT_ABI);
const erc20Interface = new ethers.Interface(IERC20_ABI);
const wethInterface = new ethers.Interface(WETH9_ABI);

export interface ClassifiedEvents {
  trades: TradeEvent[];
  transfers: TransferEvent[];
  settlements: SettlementEvent[];
}

export function partitionEventLogs(logs: Log[]): ClassifiedEvents {
  const result: ClassifiedEvents = {
    transfers: [],
    trades: [],
    settlements: [],
  };

  logs.forEach((log, index) => {
    // We are only interested in Transfer Events from erc20 contracts
    // along with Settlement and Trade Events from the Settlement contract
    // All other event emissions can be ignored for our purposes.
    const possibleTransfer = tryParseERC20Transfer(log);
    const possibleWethAction = tryParseWethAction(log);
    if (possibleTransfer || possibleWethAction) {
      const transfer = (possibleTransfer ??
        possibleWethAction) as TransferEvent;
      if (transferInvolves(transfer, SETTLEMENT_CONTRACT_ADDRESS)) {
        result.transfers.push(transfer);
      }
      return;
    }

    const possibleSettlementEvent = tryParseSettlementEventLog(log, index);
    if (possibleSettlementEvent) {
      const settlementEventLog = possibleSettlementEvent;
      // Relevant Event Types
      if (isTradeEvent(settlementEventLog)) {
        result.trades.push(settlementEventLog);
      } else if (isSettlementEvent(settlementEventLog)) {
        result.settlements.push(settlementEventLog);
      } else {
        // Placeholder for other Settlement Contract Events (e.g. Interaction)
      }
      return;
    }
    // Placeholder for any event emitted not by erc20 token or Settlement contract.
    // Examples here include WETH deposit/withdrawals, AMM Swaps etc.
  });
  return result;
}

export function tryParseSettlementEventLog(
  log: Log,
  index: number
): SettlementEvent | TradeEvent | null {
  const settlementEventLog = settlementInterface.parseLog(log);
  if (settlementEventLog === null) return null;
  // Relevant Event Types
  if (settlementEventLog.name == "Trade") {
    const { owner } = settlementEventLog.args;
    return { owner } as TradeEvent;
  } else if (settlementEventLog.name == "Settlement") {
    const { solver } = settlementEventLog.args;
    return {
      solver,
      logIndex: index,
    } as SettlementEvent;
  } else {
    // Placeholder for other Settlement Contract Events (e.g. Interaction)
    return null;
  }
}

export function tryParseERC20Transfer(log: Log): TransferEvent | null {
  const transferEventLog = erc20Interface.parseLog(log);
  if (transferEventLog === null || transferEventLog.name !== "Transfer")
    return null;
  const { from, to, value } = transferEventLog.args;
  return {
    token: log.address,
    from,
    to,
    amount: BigInt(value),
  };
}

export function tryParseWethAction(log: Log): TransferEvent | null {
  if (log.address !== WETH_TOKEN_ADDRESS) return null; // Not emitted by WETH Contract!
  const eventLog = wethInterface.parseLog(log);
  if (eventLog === null || !["Deposit", "Withdrawal"].includes(eventLog.name)) {
    return null;
  }

  const { src, dst, wad } = eventLog.args;
  const isDeposit = eventLog.name === "Deposit";

  const to = isDeposit ? dst : ethers.ZeroAddress;
  const from = isDeposit ? ethers.ZeroAddress : src;
  return {
    token: log.address,
    from,
    to,
    amount: BigInt(wad),
  };
}
