import { SettlementEvent, TradeEvent, TransferEvent } from "./models";
import { Log } from "@tenderly/actions";
import { transferInvolves } from "./utils";
import { ethers } from "ethers";
import { abi as SETTLEMENT_ABI } from "@cowprotocol/contracts/lib/contracts/GPv2Settlement.json";
import { abi as IERC20_ABI } from "@cowprotocol/contracts/lib/contracts/IERC20.json";
import { address as SETTLEMENT_CONTRACT_ADDRESS } from "@cowprotocol/contracts/deployments/mainnet/GPv2Settlement.json";

export interface ClassifiedEvents {
  trades: TradeEvent[];
  transfers: TransferEvent[];
  settlements: SettlementEvent[];
}

export function partitionEventLogs(logs: Log[]): ClassifiedEvents {
  let result: ClassifiedEvents = {
    transfers: [],
    trades: [],
    settlements: [],
  };
  const settlementInterface = new ethers.Interface(SETTLEMENT_ABI);
  const erc20Interface = new ethers.Interface(IERC20_ABI);
  logs.forEach((log, index) => {
    // We are only interested in Transfer Events from erc20 contracts
    // along with Settlement and Trade Events from the Settlement contract
    // All other event emissions can be ignored for our purposes.
    const transferEventLog = erc20Interface.parseLog(log);
    const settlementEventLog = settlementInterface.parseLog(log);
    if (transferEventLog != null && transferEventLog.name === "Transfer") {
      const { from, to, value } = transferEventLog.args;
      const transfer: TransferEvent = {
        from,
        to,
        amount: BigInt(value),
      };
      // Is a "relevant" transfer (involving settlement contract)
      if (transferInvolves(transfer, SETTLEMENT_CONTRACT_ADDRESS)) {
        result.transfers.push(transfer);
      }
    } else if (settlementEventLog != null) {
      // Relevant Event Types
      if (settlementEventLog.name == "Trade") {
        const { owner } = settlementEventLog.args;
        result.trades.push({
          owner,
        });
      } else if (settlementEventLog.name == "Settlement") {
        const { solver } = settlementEventLog.args;
        result.settlements.push({
          solver,
          logIndex: index,
        });
      } else {
        // Placeholder for other Settlement Contract Events (e.g. Interaction)
      }
    } else {
      // Placeholder for any event emitted not by erc20 token or Settlement contract.
      // Examples here include WETH deposit/withdrawals, AMM Swaps etc.
    }
  });
  return result;
}