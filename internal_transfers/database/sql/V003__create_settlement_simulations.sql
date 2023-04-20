create table settlement_simulations
(
    -- The hash of the actual (mined) Settlement Transaction
    tx_hash  bytea NOT NULL,
    -- Relevant Settlement Data used to generate simulations
    winning_settlement jsonb NOT NULL,
    -- Structure of the SimulationData is here: internal_transfers/actions/src/simulate/interface.ts
    complete jsonb NOT NULL,
    reduced  jsonb NOT NULL,

    PRIMARY KEY (tx_hash)
);

CREATE INDEX simulation_idx ON settlement_simulations (tx_hash);
