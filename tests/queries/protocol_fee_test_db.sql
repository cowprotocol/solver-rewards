DROP TABLE IF EXISTS settlements;
DROP TABLE IF EXISTS auction_transaction;
DROP TABLE IF EXISTS settlement_scores;
DROP TABLE IF EXISTS auction_prices;
DROP TABLE IF EXISTS orders;
DROP TYPE IF EXISTS OrderKind;
DROP TYPE IF EXISTS OrderClass;
DROP TABLE IF EXISTS trades;
DROP TABLE IF EXISTS order_execution;
DROP TABLE IF EXISTS fee_policies;
DROP TYPE IF EXISTS PolicyKind;

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
  auction_id       bigint PRIMARY KEY,
  winner           bytea          NOT NULL,
  winning_score    numeric(78, 0) NOT NULL,
  reference_score  numeric(78, 0) NOT NULL,
  block_deadline   bigint         NOT NULL,
  simulation_block bigint         NOT NULL
);

CREATE TABLE IF NOT EXISTS auction_prices
(
  auction_id bigint NOT NULL,
  token bytea NOT NULL,
  price  numeric(78, 0) NOT NULL,

  PRIMARY KEY (auction_id, token)
);

-- orders table
CREATE TYPE OrderKind AS ENUM ('buy', 'sell');
CREATE TYPE OrderClass AS ENUM ('market', 'limit');

CREATE TABLE orders (
    uid bytea PRIMARY KEY,
    sell_token bytea NOT NULL,
    buy_token bytea NOT NULL,
    sell_amount numeric(78,0) NOT NULL,
    buy_amount numeric(78,0) NOT NULL,
    fee_amount numeric(78,0) NOT NULL,
    kind OrderKind NOT NULL,
    partially_fillable boolean NOT NULL,
    full_fee_amount numeric(78,0) NOT NULL,
    class OrderClass NOT NULL
);

CREATE TABLE IF NOT EXISTS trades
(
  block_number bigint         NOT NULL,
  log_index    bigint         NOT NULL,
  order_uid    bytea          NOT NULL,
  sell_amount  numeric(78, 0) NOT NULL,
  buy_amount   numeric(78, 0) NOT NULL,
  fee_amount   numeric(78, 0) NOT NULL,

  PRIMARY KEY (block_number, log_index)
);

CREATE TABLE IF NOT EXISTS order_execution
(
  order_uid bytea NOT NULL,
  auction_id bigint NOT NULL,
  reward double precision NOT NULL,
  surplus_fee numeric(78, 0) NOT NULL,
  solver_fee numeric(78, 0),

  PRIMARY KEY (order_uid, auction_id)
);

CREATE TYPE PolicyKind AS ENUM ('surplus', 'volume');

CREATE TABLE fee_policies (
  auction_id bigint NOT NULL,
  order_uid bytea NOT NULL,
  -- The order in which the fee policies are inserted and applied.
  application_order SERIAL NOT NULL,
  -- The type of the fee policy.
  kind PolicyKind NOT NULL,
  -- The fee should be taken as a percentage of the price improvement. The value is between 0 and 1.
  surplus_factor double precision,
  -- Cap the fee at a certain percentage of the order volume. The value is between 0 and 1.
  max_volume_factor double precision,
  -- The fee should be taken as a percentage of the order volume. The value is between 0 and 1.
  volume_factor double precision,
  PRIMARY KEY (auction_id, order_uid, application_order)
);

TRUNCATE settlements;
TRUNCATE auction_transaction;
TRUNCATE settlement_scores;
TRUNCATE auction_prices;
TRUNCATE orders;
TRUNCATE trades;
TRUNCATE fee_policies;


INSERT INTO settlements (block_number, log_index, solver, tx_hash, tx_from, tx_nonce)
VALUES (1, 10, '\x01'::bytea, '\x01'::bytea, '\x01'::bytea, 1),
       (2, 10, '\x02'::bytea, '\x02'::bytea, '\x02'::bytea, 1),
       (3, 10, '\x01'::bytea, '\x03'::bytea, '\x01'::bytea, 2),
       (4, 10, '\x02'::bytea, '\x04'::bytea, '\x02'::bytea, 2),
       (5, 10, '\x01'::bytea, '\x05'::bytea, '\x01'::bytea, 3),
       (6, 10, '\x02'::bytea, '\x06'::bytea, '\x02'::bytea, 3);

INSERT INTO auction_transaction (auction_id, tx_from, tx_nonce)
VALUES (1, '\x01'::bytea, 1),
       (2, '\x02'::bytea, 1),
       (3, '\x01'::bytea, 2),
       (4, '\x02'::bytea, 2),
       (5, '\x01'::bytea, 3),
       (6, '\x02'::bytea, 3);

INSERT INTO settlement_scores (auction_id, winning_score, reference_score, winner, block_deadline, simulation_block)
VALUES (1, 5000000000000000000, 4000000000000000000, '\x01'::bytea, 10, 0),
       (2, 6000000000000000000, 3000000000000000000, '\x02'::bytea, 11, 1),
       (3, 21000000000000000000, 3000000000000000000, '\x01'::bytea, 12, 2),
       (4, 21000000000000000000, 3000000000000000000, '\x02'::bytea, 12, 2),
       (5, 5000000000000000000, 3000000000000000000, '\x01'::bytea, 14, 4),
       (6, 10000000000000000000, 9000000000000000000, '\x02'::bytea, 15, 5);

INSERT INTO auction_prices (auction_id, token, price)
VALUES (1, '\x01', 500000000000000000000000000),
(1, '\x02', 500000000000000),
(2, '\x01', 500000000000000000000000000),
(2, '\x02', 500000000000000),
(3, '\x01', 500000000000000000000000000),
(3, '\x02', 500000000000000),
(4, '\x01', 500000000000000000000000000),
(4, '\x02', 500000000000000),
(5, '\x01', 500000000000000000000000000),
(5, '\x02', 500000000000000),
(6, '\x01', 500000000000000000000000000),
(6, '\x02', 500000000000000);

INSERT INTO orders (uid, sell_token, buy_token, sell_amount, buy_amount, fee_amount, kind, partially_fillable, full_fee_amount, class)
VALUES ('\x01'::bytea, '\x01'::bytea, '\x02'::bytea, 95000000, 94000000000000000000, 5000000, 'sell', 'f', 5000000, 'market'), -- sell market order
('\x02'::bytea, '\x01'::bytea, '\x02'::bytea, 101000000, 100000000000000000000, 5000000, 'buy', 'f', 5000000, 'market'), -- buy market order
('\x03'::bytea, '\x01'::bytea, '\x02'::bytea, 100000000, 100000000000000000000, 0, 'sell', 't', 0, 'limit'), -- partially fillable sell limit order
('\x04'::bytea, '\x01'::bytea, '\x02'::bytea, 100000000, 100000000000000000000, 0, 'buy', 't', 0, 'limit'), -- partially fillable buy limit order
('\x05'::bytea, '\x01'::bytea, '\x02'::bytea, 100000000, 94000000000000000000, 0, 'sell', 'f', 0, 'limit'), -- in market sell limit order
('\x06'::bytea, '\x01'::bytea, '\x02'::bytea, 106000000, 100000000000000000000, 0, 'buy', 'f', 0, 'limit'); -- in market buy limit order

INSERT INTO trades (block_number, log_index, order_uid, sell_amount, buy_amount, fee_amount)
VALUES (1, 0, '\x01'::bytea, 100000000, 95000000000000000000, 5000000),
(2, 0, '\x02'::bytea, 106000000, 100000000000000000000, 5000000),
(3, 0, '\x03'::bytea, 100000000, 101000000000000000000, 0),
(4, 0, '\x04'::bytea, 99000000, 100000000000000000000, 0),
(5, 0, '\x05'::bytea, 100000000, 95000000000000000000, 0),
(6, 0, '\x06'::bytea, 105000000, 100000000000000000000, 0);

INSERT INTO order_execution (order_uid, auction_id, reward, surplus_fee, solver_fee)
VALUES ('\x03'::bytea, 3, 0, 5931372, NULL),
('\x04'::bytea, 4, 0, 6000000, NULL),
('\x05'::bytea, 5, 0, 6000000, NULL),
('\x06'::bytea, 6, 0, 6000000, NULL);

INSERT INTO fee_policies (auction_id, order_uid, application_order, kind, surplus_factor, max_volume_factor, volume_factor)
VALUES (3, '\x03'::bytea, 3, 'surplus', 0.5, 0.02, NULL),
(4, '\x04'::bytea, 4, 'surplus', 0.75, 0.1, NULL),
(5, '\x05'::bytea, 5, 'volume', NULL, NULL, 0.0015),
(6, '\x06'::bytea, 6, 'surplus', 0.9, 0.01, NULL);
