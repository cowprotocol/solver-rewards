CREATE TABLE internalized_imbalances
(
    tx_hash bytea NOT NULL,
    token   bytea NOT NULL,
    amount  numeric(78),

    PRIMARY KEY (tx_hash, token)
);

CREATE INDEX imbalances_idx ON internalized_imbalances (tx_hash);
CREATE INDEX imbalances_idx_1 ON internalized_imbalances (token);
