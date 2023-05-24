import { EnsoSimulator } from "../src/simulate/enso";
import { TenderlySimulator } from "../src/simulate/tenderly";
import { TransactionSimulator } from "../src/simulate/interface";
import { parse } from "ts-command-line-args";
import { DuneClient } from "@cowprotocol/ts-dune-client";
import { getDB } from "../src/database";
import { AbstractProvider, ethers } from "ethers";
import { Queryable } from "@databases/pg";

const dotenv = require("dotenv");

dotenv.config();

interface CommandArgs {
  // YYYY-MM-DD
  dateString?: string;
  txHashes?: string[];
}

interface Environment {
  simulator: TransactionSimulator;
  dune?: DuneClient;
  provider: AbstractProvider;
  db: Queryable;
}

interface RuntimeArgs {
  env: Environment;
  cmd: CommandArgs;
}

export function getArgs(): RuntimeArgs {
  const {
    DUNE_API_KEY,
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

  let simulator: TransactionSimulator = new EnsoSimulator(
    "http://127.0.0.1:8080/api/v1/simulate"
  );
  if (
    ![TENDERLY_ACCESS_KEY, TENDERLY_USER, TENDERLY_PROJECT].includes(undefined)
  ) {
    console.log("Using Tenderly Simulator");
    simulator = new TenderlySimulator(
      TENDERLY_USER!,
      TENDERLY_PROJECT!,
      TENDERLY_ACCESS_KEY!
    );
  }
  const dune = new DuneClient(DUNE_API_KEY!);
  const db = getDB(DB_URL);
  const provider = ethers.getDefaultProvider(NODE_URL);

  return {
    env: {
      simulator,
      dune,
      db,
      provider,
    },
    cmd: parse<CommandArgs>({
      dateString: { type: String, optional: true },
      txHashes: { type: String, multiple: true, optional: true },
    }),
  };
}
