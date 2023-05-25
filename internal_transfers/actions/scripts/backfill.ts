import { backFillTokenImbalances } from "./lib";
import { EnsoSimulator } from "../src/simulate/enso";
import { TenderlySimulator } from "../src/simulate/tenderly";
import { validateDate } from "../src/utils";
import { TransactionSimulator } from "../src/simulate/interface";
import { parse } from "ts-command-line-args";
const dotenv = require("dotenv");

dotenv.config();
interface RuntimeArgs {
  // YYYY-MM-DD
  dateFrom: string;
  dateTo: string;
}

const {
  DUNE_API_KEY,
  DB_URL,
  NODE_URL,
  TENDERLY_ACCESS_KEY,
  TENDERLY_USER,
  TENDERLY_PROJECT,
} = process.env;

if (!DUNE_API_KEY) {
  throw new Error("Missing DUNE_API_KEY");
}
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

function validateDate(value: string): string {
  if (!DATE_REGEX.test(value)) {
    throw new Error("Invalid date format. Please use the YYYY-MM-DD format.");
  }
  return value;
}

export const args = parse<RuntimeArgs>({
  dateFrom: validateDate,
  dateTo: validateDate,
});

backFillTokenImbalances(
  args.dateFrom,
  args.dateTo,
  DB_URL,
  NODE_URL,
  DUNE_API_KEY,
  simulator
).then(() => console.log("Execution Complete"));
