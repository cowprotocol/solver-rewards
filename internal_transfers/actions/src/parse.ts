import { SettlementEvent, TradeEvent, TransferEvent } from "./models";
import { Log } from "@tenderly/actions";
import { addressFromBytes32, transferInvolves } from "./utils";

export const SETTLEMENT_CONTRACT_ADDRESS =
  "0x9008d19f58aabd9ed0d60971565aa8510560ab41";
export const SETTLEMENT_EVENT_TOPIC =
  "0x40338ce1a7c49204f0099533b1e9a7ee0a3d261f84974ab7af36105b8c4e9db4";
export const TRANSFER_EVENT_TOPIC =
  "0xddf252ad1be2c89b69c2b068fc378daa952ba7f163c4a11628f55a4df523b3ef";
export const TRADE_EVENT_TOPIC =
  "0xa07a543ab8a018198e99ca0184c93fe9050a79400a0a723441f84de1d972cc17";

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
  logs.forEach((log, index) => {
    const topics = log.topics;
    const eventTopic = topics[0];

    if (eventTopic === TRANSFER_EVENT_TOPIC) {
      const transfer: TransferEvent = {
        to: addressFromBytes32(topics[2]),
        from: addressFromBytes32(topics[1]),
        amount: BigInt(log?.data),
      };
      // Is a "relevant" transfer (involving settlement contract)
      if (transferInvolves(transfer, SETTLEMENT_CONTRACT_ADDRESS)) {
        result.transfers.push(transfer);
      }
    } else if (eventTopic === TRADE_EVENT_TOPIC) {
      result.trades.push({
        owner: addressFromBytes32(topics[1]),
      });
    } else if (eventTopic === SETTLEMENT_EVENT_TOPIC) {
      result.settlements.push({
        solver: addressFromBytes32(topics[1]),
        log_index: index,
      });
    } else {
      // Other, currently ignored, event topic.
      // Examples here include WETH deposit/withdrawals
    }
  });
  return result;
}
