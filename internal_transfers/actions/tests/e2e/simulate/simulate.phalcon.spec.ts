import {failTx, successTx} from "./testSimData.json";
import { PhalconSimulator } from "../../../src/simulate/phalcon";

// Note had to change localhost to 127.0.0.1
// cf: https://github.com/axios/axios/issues/3821#issuecomment-1047276564
const simulator = new PhalconSimulator("http://127.0.0.1:8080/api/v1/simulate");

describe("Phalcon Simulator", () => {
  test("simulate() returns expected output on successful simulation", async () => {
    const simulation = await simulator.simulate(successTx);
    expect(simulation).toMatchSnapshot();
  }, 500000000);
  test("simulate() returns expected output on failed simulation", async () => {
    await expect(simulator.simulate(failTx)).rejects.toThrow();
  });
});
