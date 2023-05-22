import { backFillTokenImbalances } from "./lib";
import { EnsoSimulator } from "../src/simulate/enso";

const simulator = new EnsoSimulator("http://127.0.0.1:8080/api/v1/simulate");

backFillTokenImbalances("2023-01-01", simulator).then((_) =>
  console.log("Execution Complete")
);
