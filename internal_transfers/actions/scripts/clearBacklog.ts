import { clearBacklog } from "./lib";
import { EnsoSimulator } from "../src/simulate/enso";
import { TenderlySimulator } from "../src/simulate/tenderly";
import { TransactionSimulator } from "../src/simulate/interface";
const dotenv = require("dotenv");

dotenv.config();
const {
  DB_URL,
  NODE_URL,
  TENDERLY_ACCESS_KEY,
  TENDERLY_USER,
  TENDERLY_PROJECT,
} = process.env;

if (!DB_URL) {
  throw new Error("Missing DB_URL");
}
if (!NODE_URL) {
  throw new Error("Missing NODE_URL");
}

let simulator: TransactionSimulator;
if (TENDERLY_ACCESS_KEY && TENDERLY_USER && TENDERLY_PROJECT) {
  console.log("Using Tenderly Simulator");
  simulator = new TenderlySimulator(
    TENDERLY_USER,
    TENDERLY_PROJECT,
    TENDERLY_ACCESS_KEY
  );
} else {
  console.log("Using Default (Local Enso) Simulator");
  simulator = new EnsoSimulator("http://127.0.0.1:8080/api/v1/simulate");
}

console.log(DB_URL)
clearBacklog(DB_URL, NODE_URL, simulator).then(() =>
  console.log("Execution Complete")
);
