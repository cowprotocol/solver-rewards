DROP TABLE IF EXISTS settlements;
DROP TABLE IF EXISTS auction_transaction;
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

  PRIMARY KEY (block_number, log_index)
);

CREATE INDEX settlements_tx_from_tx_nonce ON settlements (tx_from, tx_nonce);

CREATE TABLE IF NOT EXISTS auction_transaction
(
  auction_id bigint PRIMARY KEY,
  tx_from    bytea  NOT NULL,
  tx_nonce   bigint NOT NULL,
  UNIQUE (tx_from, tx_nonce)
);

CREATE TABLE IF NOT EXISTS auction_participants
(
  auction_id  bigint,
  participant bytea
);

CREATE TABLE IF NOT EXISTS settlement_scores
(
  auction_id      bigint PRIMARY KEY,
  block_deadline  bigint         NOT NULL,
  winner          bytea          NOT NULL,
  winning_score   numeric(78, 0) NOT NULL,
  reference_score numeric(78, 0) NOT NULL
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
TRUNCATE auction_transaction;
TRUNCATE auction_participants;
TRUNCATE settlement_scores;
TRUNCATE settlement_observations;

INSERT INTO settlements (block_number, log_index, solver, tx_hash, tx_from, tx_nonce)
VALUES (1, 0, '\x5111'::bytea, '\x7111'::bytea, '\x5111'::bytea, 1),
       (2, 0, '\x5222'::bytea, '\x7222'::bytea, '\x5222'::bytea, 1),
       (5, 0, '\x5111'::bytea, '\x7333'::bytea, '\x5111'::bytea, 2),
       -- would the following entry be in the data base? (submitted too late) -- YES
       (20, 0, '\x5111'::bytea, '\x7444'::bytea, '\x5111'::bytea, 3),
       (25, 0, '\x5111'::bytea, '\x7555'::bytea, '\x5111'::bytea, 4),
       (26, 0, '\x5111'::bytea, '\x7666'::bytea, '\x5111'::bytea, 6);

INSERT INTO auction_transaction (auction_id, tx_from, tx_nonce)
VALUES (1, '\x5111'::bytea, 1),
       (2, '\x5222'::bytea, 1),
       (5, '\x5111'::bytea, 2),
       (6, '\x5111'::bytea, 3), -- would that entry be in the data base? (submitted too late)
       (7, '\x5111'::bytea, 4),
       (8, '\x5111'::bytea, 5), -- would that entry be in the data base? (failed transaction)
       (9, '\x5111'::bytea, 6),
       (10, '\x5333'::bytea, 1); -- would that entry be in the data base? (failed transaction)

INSERT INTO auction_participants (auction_id, participant)
VALUES (1, '\x5222'::bytea),
       (1, '\x5333'::bytea),
       (1, '\x5111'::bytea),
       (2, '\x5444'::bytea),
       (2, '\x5333'::bytea),
       (2, '\x5222'::bytea),
       (3, '\x5444'::bytea),
       (3, '\x5333'::bytea),
       (3, '\x5111'::bytea),
       (5, '\x5444'::bytea),
       (5, '\x5333'::bytea),
       (5, '\x5111'::bytea),
       (6, '\x5444'::bytea),
       (6, '\x5333'::bytea),
       (6, '\x5111'::bytea),
       (7, '\x5111'::bytea),
       (8, '\x5111'::bytea),
       (9, '\x5444'::bytea),
       (9, '\x5333'::bytea),
       (9, '\x5111'::bytea),
       (10, '\x5444'::bytea),
       (10, '\x5333'::bytea);

INSERT INTO settlement_scores (auction_id, block_deadline, winning_score, reference_score, winner)
VALUES (1, 10, 5000000000000000000, 4000000000000000000, '\x5111'::bytea),
       (2, 11, 6000000000000000000, 3000000000000000000, '\x5222'::bytea),
       (3, 12, 21000000000000000000, 3000000000000000000, '\x5111'::bytea),
       (5, 14, 5000000000000000000, 3000000000000000000, '\x5111'::bytea),  -- jump in auction id
       (6, 15, 10000000000000000000, 9000000000000000000, '\x5111'::bytea), -- settled too late
       (7, 30, 5000000000000000000, 0, '\x5111'::bytea),                    -- no competition
       (8, 35, 5000000000000000000, 0, '\x5111'::bytea),                    -- no competition, failed transaction
       (9, 36, 5000000000000000000, 1000000000000000000, '\x5111'::bytea),  -- score larger than quality
       (10, 37, 5000000000000000000, 4000000000000000000, '\x5333'::bytea); -- participant with net negative payment

INSERT INTO settlement_observations (block_number, log_index, gas_used, effective_gas_price, surplus, fee)
VALUES (1, 0, 100000, 2000000000, 6000000000000000000, 200000000000000),
       (2, 0, 150000, 3000000000, 12000000000000000000, 400000000000000),
       (5, 0, 100000, 2000000000, 5000000000000000000, 250000000000000),
       -- Depends on backend (setting surplus and fee to zero).
       -- I would prefer to use the real numbers. What is backend gonna do.
       (20, 0, 100000, 2000000000, 0, 0), -- would that entry be in the data base? (submitted too late)
       (25, 0, 100000, 2000000000, 6000000000000000000, 200000000000000),
       (26, 0, 100000, 2000000000, 0, 400000000000000);
