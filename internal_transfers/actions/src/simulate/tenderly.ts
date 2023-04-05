import axios from "axios";
import { TxSimulator } from "./interface";

export class TenderlySimulator extends TxSimulator {
  BASE_URL = "https://api.tenderly.co/api";
  user: string;
  project: string;
  accessKey: string;

  constructor(user: string, project: string, accessKey: string) {
    super();
    this.user = user;
    this.project = project;
    this.accessKey = accessKey;
  }
  async simulate(
    contractAddress: string,
    sender: string,
    callData: string,
    value: string = "0",
    save: boolean = false,
    blockNumber?: number
  ): Promise<any> {
    const SIMULATE_URL = `${this.BASE_URL}/v1/account/${this.user}/project/${this.project}/simulate`;
    try {
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
          value: "0",
          // simulation config (tenderly specific)
          save_if_fails: save,
          save: save,
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
      return response.data;
    } catch (error: any) {
      if (error.response) {
        // The request was made and the server responded with a bad status code
        console.error(
          `Response status ${error.response.status} - ${error.response.statusText}`
        );
      } else if (error.message) {
        // Something happened in setting up the request that triggered an Error
        console.error(`Message: ${error.message}`);
      }
      throw Error(error);
    }
  }
}
