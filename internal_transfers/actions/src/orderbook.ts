import { WinningSettlementData } from "./models";
import axios from "axios";

// https://api.cow.fi/docs/#/
const ORDERBOOK_API_URL =
  "https://api.cow.fi/mainnet/api/v1/solver_competition/by_tx_hash";
// I think we should exclude Barn (or have a seprate DB for this)
// const BARN_ORDERBOOK_API_URL =
//   "https://barn.api.cow.fi/mainnet/api/v1/solver_competition/by_tx_hash";

// Fetches solver_competition for `tx_hash` from orderbook API via:
// api.cow.fi/mainnet/api/v1/solver_competition/by_tx_hash/{tx_hash}
// Parses only the relevant fields from the results and returns this info.
/**
 * @param {string}  txHash - transaciton hash of a settlement event.
 * @returns {WinningSettlementData}
 */
export async function getSettlementCompeitionData(
  txHash: string
): Promise<WinningSettlementData | undefined> {
  // TODO (the following are nice to have, but would affect performance of workflow)
  // 1. assert isValidTxHash (regex:  /^0x([A-Fa-f0-9]{64})$/ )
  // 2. query orderbook API
  // 3. assert isActualTxHash: web3.eth.getTransactionReceipt(txHash) -- Requires EVM Node.
  // 4. assert isSettlementTransaction(txReceipt)
  // Note that, its cheaper and faster to query orderbook API for the data we want.
  // If its not there, Prod then Barn, we could attempt to validate that the txHash was legit.

  // Check Prod First
  const url = `${ORDERBOOK_API_URL}/${txHash}`;
  try {
    const response = await axios.get(url);
    if (response.status === 404) {
      // TODO steps 3 and 4 above (if we want to)
      throw `Invalid settlement transaction ${txHash}`;
    }
    // console.log(`received response ${JSON.stringify(response.data, null, 2)}`);

    // The Orderbook, stores all solution submissions sorted by the objective criteria.
    // The winning solution is the last entry of the `solutions` array.
    const solutionArray = response.data.solutions;

    const winningSolution = solutionArray[solutionArray.length - 1];
    // console.log(JSON.stringify(winningSolution, null, 2))

    // Note that old records have solver = ZeroAddress! We need to rectify this (use txReceipt!)
    const solver = winningSolution.solverAddress;

    return {
      simulationBlock: response.data.competitionSimulationBlock,
      solver,
      reducedCallData: winningSolution.callData,
      fullCallData: winningSolution.uninternalizedCallData,
    };
  } catch (exception) {
    if (axios.isAxiosError(exception)) {
      // Not Found.
      // WTF is wrong with this? status is always 404 but I can't get it.
      // console.log(JSON.stringify(exception, null, 2))
      // console.log(exception.status)
      // console.log(`Not Found ${JSON.stringify(exception)}`);
      return undefined;
    } else {
      throw `ERROR received from ${url}: ${exception}`;
    }
  }
}
