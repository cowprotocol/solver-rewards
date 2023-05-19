import { EnsoSimulator } from "../../../src/simulate/enso";
import {failTx, successTx} from "./testSimData.json";

// Note had to change localhost to 127.0.0.1
// cf: https://github.com/axios/axios/issues/3821#issuecomment-1047276564
const simulator = new EnsoSimulator("http://127.0.0.1:8080/api/v1/simulate");

describe.skip("Enso Simulator", () => {
  test("simulate() returns expected output on successful simulation", async () => {
    const simulation = await simulator.simulate(successTx);
    expect(simulation).toMatchSnapshot();
  }, 500000000);
  test("simulate() returns expected output on failed simulation", async () => {
    await expect(simulator.simulate(failTx)).rejects.toThrow();
  });
});
