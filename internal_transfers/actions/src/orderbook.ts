import { WinningSettlementData } from "./models";
import axios from "axios";

// https://api.cow.fi/docs/#/
const PROD_API_URL =
  "https://api.cow.fi/mainnet/api/v1/solver_competition/by_tx_hash";
const BARN_API_URL =
  "https://barn.api.cow.fi/mainnet/api/v1/solver_competition/by_tx_hash";

async function getWinningSettlementFromOrderbookAPI(
  apiUrl: string
): Promise<WinningSettlementData | undefined> {
  try {
    const response = await axios.get(apiUrl);

    // The Orderbook, stores all solution submissions sorted by the objective criteria.
    // The winning solution is the last entry of the `solutions` array.
    const solutionArray = response.data.solutions;
    const winningSolution = solutionArray[solutionArray.length - 1];
    // TODO - Note that old records have solver = ZeroAddress!
    //  We need to rectify this (use txReceipt or whatever Tenderly web-action provides)
    const solver = winningSolution.solverAddress;

    return {
      simulationBlock: response.data.competitionSimulationBlock,
      solver,
      reducedCallData: winningSolution.callData,
      fullCallData: winningSolution.uninternalizedCallData,
    };
  } catch (exception) {
    if (axios.isAxiosError(exception)) {
      if (exception.response?.status != 404) {
        throw new Error(
          `ERROR response status from ${apiUrl}: ${exception.response}`
        );
      }
      // Not Found (404) is an expected response from the API.
      // Could be for any of the following reasons:
      // 1. !isValidTxHash (regex:  /^0x([A-Fa-f0-9]{64})$/ )
      // 2. !isActualTxHash: web3.eth.getTransactionReceipt(txHash) -- Requires EVM Node.
      // 3. !isSettlementTransaction(txReceipt)
      // 4. !correctDB
      // TODO - might be nice to pre-validate input, but would affect performance of workflow
      //  its cheaper and faster to query orderbook API for the data we want without validation.
      return undefined;
    } else {
      throw new Error(
        `ERROR unexpected response received from ${apiUrl}: ${exception}`
      );
    }
  }
}

/** Fetches solver_competition for `tx_hash` from orderbook API via:
 * api.cow.fi/mainnet/api/v1/solver_competition/by_tx_hash/{tx_hash}
 * Parses only the relevant fields from the results and returns this info.
 *
 * @param {string}  txHash - transaction hash of a settlement event.
 * @returns {WinningSettlementData}
 */
export async function getSettlementCompetitionData(
  txHash: string
): Promise<WinningSettlementData | undefined> {
  // Try fetching from Production first
  let result = await getWinningSettlementFromOrderbookAPI(
    `${PROD_API_URL}/${txHash}`
  );
  if (result !== undefined) return result;

  // If it was not found/undefined try fetching from Barn.
  return await getWinningSettlementFromOrderbookAPI(
    `${BARN_API_URL}/${txHash}`
  );
}
