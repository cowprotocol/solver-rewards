export abstract class TxSimulator {
  /**
   * Simulates the given `callData` uses whatever means of EVM transaction simulation at `block_number`.
   * Returns sufficiently relevant parts of the simulation to build Settlement Transfers.
   * Simulation request would correspond to the following transaction data:
   * {
   *      "to": contractAddress,
   *      "from": sender,
   *      "data": callData
   *      "value": 0,
   * }
   *
   * @param {string} contractAddress - Ethereum address transaction should be sent to.
   * @param {string} sender - Ethereum address of transaction sender
   * @param {string} callData - 0x-prefixed string representing transaction data to simulate
   * @param {string} value - Amount of Ether to send along with transaction.
   * @param {boolean} save - Flag indicating whether the simulation should be saved.
   * @param {number} blockNumber - Block at which simulation should be made.
   * @returns JSON representation of corresponding simulation result (i.e. "untyped" simulation results).
   */
  abstract simulate(
    // essential transaction data
    contractAddress: string,
    sender: string,
    callData: string,
    value: string,
    // tenderly configs
    save: boolean,
    blockNumber?: number
  ): Promise<any>;
}
