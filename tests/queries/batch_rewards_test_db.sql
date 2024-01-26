DROP TABLE IF EXISTS settlements;
DROP TABLE IF EXISTS auction_participants;
DROP TABLE IF EXISTS settlement_scores;
DROP TABLE IF EXISTS settlement_observations;

CREATE TABLE IF NOT EXISTS settlements
(
  block_number bigint NOT NULL,
  log_index    bigint NOT NULL,
  solver       bytea  NOT NULL,
  tx_hash      bytea  NOT NULL,
  tx_from      bytea  NOT NULL,
  tx_nonce     bigint NOT NULL,
  auction_id   bigint,

  PRIMARY KEY (block_number, log_index)
);

CREATE INDEX settlements_tx_from_tx_nonce ON settlements (tx_from, tx_nonce);

CREATE TABLE IF NOT EXISTS auction_participants
(
  auction_id  bigint,
  participant bytea
);

CREATE TABLE IF NOT EXISTS settlement_scores
(
  auction_id       bigint PRIMARY KEY,
  winner           bytea          NOT NULL,
  winning_score    numeric(78, 0) NOT NULL,
  reference_score  numeric(78, 0) NOT NULL,
  block_deadline   bigint         NOT NULL,
  simulation_block bigint         NOT NULL
);

-- Populated after block finalization via transactionReceipt.
CREATE TABLE IF NOT EXISTS settlement_observations
(
  block_number        bigint         NOT NULL,
  log_index           bigint         NOT NULL,
  gas_used            numeric(78, 0) NOT NULL,
  effective_gas_price numeric(78, 0) NOT NULL,
  surplus             numeric(78, 0) NOT NULL,
  fee                 numeric(78, 0) NOT NULL,

  PRIMARY KEY (block_number, log_index)
);


TRUNCATE settlements;
TRUNCATE auction_participants;
TRUNCATE settlement_scores;
TRUNCATE settlement_observations;


INSERT INTO settlements (block_number, log_index, solver, tx_hash, tx_from, tx_nonce, auction_id)
VALUES (1, 10, '\x5111111111111111111111111111111111111111'::bytea, '\x7111'::bytea, '\x5111111111111111111111111111111111111111'::bytea, 1, 1),
       (2, 10, '\x5222222222222222222222222222222222222222'::bytea, '\x7222'::bytea, '\x5222222222222222222222222222222222222222'::bytea, 1, 2),
       (5, 10, '\x5111111111111111111111111111111111111111'::bytea, '\x7333'::bytea, '\x5111111111111111111111111111111111111111'::bytea, 2, 5),
       -- would the following entry be in the data base? (submitted too late) -- YES
       (20, 10, '\x5111111111111111111111111111111111111111'::bytea, '\x7444'::bytea, '\x5111111111111111111111111111111111111111'::bytea, 3, 6),
       (25, 10, '\x5111111111111111111111111111111111111111'::bytea, '\x7555'::bytea, '\x5111111111111111111111111111111111111111'::bytea, 4, 7),
       (26, 10, '\x5111111111111111111111111111111111111111'::bytea, '\x7666'::bytea, '\x5111111111111111111111111111111111111111'::bytea, 6, 9);

INSERT INTO auction_participants (auction_id, participant)
VALUES (1, '\x5222222222222222222222222222222222222222'::bytea),
       (1, '\x5333333333333333333333333333333333333333'::bytea),
       (1, '\x5111111111111111111111111111111111111111'::bytea),
       (2, '\x5444444444444444444444444444444444444444'::bytea),
       (2, '\x5333333333333333333333333333333333333333'::bytea),
       (2, '\x5222222222222222222222222222222222222222'::bytea),
       (3, '\x5444444444444444444444444444444444444444'::bytea),
       (3, '\x5333333333333333333333333333333333333333'::bytea),
       (3, '\x5111111111111111111111111111111111111111'::bytea),
       (5, '\x5444444444444444444444444444444444444444'::bytea),
       (5, '\x5333333333333333333333333333333333333333'::bytea),
       (5, '\x5111111111111111111111111111111111111111'::bytea),
       (6, '\x5444444444444444444444444444444444444444'::bytea),
       (6, '\x5333333333333333333333333333333333333333'::bytea),
       (6, '\x5111111111111111111111111111111111111111'::bytea),
       (7, '\x5111111111111111111111111111111111111111'::bytea),
       (8, '\x5111111111111111111111111111111111111111'::bytea),
       (9, '\x5444444444444444444444444444444444444444'::bytea),
       (9, '\x5333333333333333333333333333333333333333'::bytea),
       (9, '\x5111111111111111111111111111111111111111'::bytea),
       (10, '\x5444444444444444444444444444444444444444'::bytea),
       (10, '\x5333333333333333333333333333333333333333'::bytea);

INSERT INTO settlement_scores (auction_id, winning_score, reference_score, winner, block_deadline, simulation_block)
VALUES (1, 5000000000000000000, 4000000000000000000, '\x5111111111111111111111111111111111111111'::bytea, 10, 0),
       (2, 6000000000000000000, 3000000000000000000, '\x5222222222222222222222222222222222222222'::bytea, 11, 1),
       (3, 21000000000000000000, 3000000000000000000, '\x5111111111111111111111111111111111111111'::bytea, 12, 2),
       (5, 5000000000000000000, 3000000000000000000, '\x5111111111111111111111111111111111111111'::bytea, 14, 4),  -- jump in auction id
       (6, 10000000000000000000, 9000000000000000000, '\x5111111111111111111111111111111111111111'::bytea, 15, 5), -- settled too late
       (7, 5000000000000000000, 0, '\x5111111111111111111111111111111111111111'::bytea, 30, 6),                    -- no competition
       (8, 5000000000000000000, 0, '\x5111111111111111111111111111111111111111'::bytea, 35, 7),                    -- no competition, failed transaction
       (9, 5000000000000000000, 1000000000000000000, '\x5111111111111111111111111111111111111111'::bytea, 36, 8),  -- score larger than quality
       (10, 5000000000000000000, 4000000000000000000, '\x5333333333333333333333333333333333333333'::bytea, 37, 9); -- participant with net negative payment

INSERT INTO settlement_observations (block_number, log_index, gas_used, effective_gas_price, surplus, fee)
VALUES (1, 10, 100000, 2000000000, 6000000000000000000, 200000000000000),
       (2, 10, 150000, 3000000000, 12000000000000000000, 400000000000000),
       (5, 10, 100000, 2000000000, 5000000000000000000, 250000000000000),
       -- Depends on backend (setting surplus and fee to zero).
       -- I would prefer to use the real numbers. What is backend gonna do.
       (20, 10, 100000, 2000000000, 0, 0), -- would that entry be in the data base? (submitted too late)
       (25, 10, 100000, 2000000000, 6000000000000000000, 200000000000000),
       (26, 10, 100000, 2000000000, 0, 400000000000000);
