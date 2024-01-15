DROP TABLE IF EXISTS settlements;
DROP TABLE IF EXISTS auction_transaction;
DROP TABLE IF EXISTS auction_participants;
DROP TABLE IF EXISTS settlement_scores;
DROP TABLE IF EXISTS settlement_observations;
DROP TABLE IF EXISTS auction_prices;
DROP TABLE IF EXISTS orders;
DROP TYPE IF EXISTS OrderKind;
DROP TYPE IF EXISTS SigningScheme;
DROP TYPE IF EXISTS TokenBalance;
DROP TYPE IF EXISTS OrderClass;
DROP TABLE IF EXISTS order_quotes;
DROP TABLE IF EXISTS trades;
DROP TABLE IF EXISTS order_executions;
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

CREATE TABLE IF NOT EXISTS auction_prices
(
  auction_id bigint NOT NULL,
  token bytea NOT NULL,
  price  numeric(78, 0) NOT NULL,

  PRIMARY KEY (auction_id, token)
);

-- orders table
CREATE TYPE OrderKind AS ENUM ('buy', 'sell');
CREATE TYPE SigningScheme AS ENUM ('presign', 'eip712', 'ethsign');
CREATE TYPE TokenBalance AS ENUM ('erc20', 'external');
CREATE TYPE OrderClass AS ENUM ('market', 'limit');

CREATE TABLE orders (
    uid bytea PRIMARY KEY,
    owner bytea NOT NULL,
    creation_timestamp timestamptz NOT NULL,
    sell_token bytea NOT NULL,
    buy_token bytea NOT NULL,
    sell_amount numeric(78,0) NOT NULL,
    buy_amount numeric(78,0) NOT NULL,
    valid_to bigint NOT NULL,
    fee_amount numeric(78,0) NOT NULL,
    kind OrderKind NOT NULL,
    partially_fillable boolean NOT NULL,
    signature bytea NOT NULL,
    cancellation_timestamp timestamptz,
    receiver bytea NOT NULL,
    app_data bytea NOT NULL,
    signing_scheme SigningScheme NOT NULL,
    settlement_contract bytea NOT NULL,
    sell_token_balance TokenBalance NOT NULL,
    buy_token_balance TokenBalance NOT NULL,
    full_fee_amount numeric(78,0) NOT NULL,
    class OrderClass NOT NULL
);

CREATE TABLE IF NOT EXISTS order_quotes
(
  order_uid bytea PRIMARY KEY,
  gas_amount double precision NOT NULL,
  gas_price double precision NOT NULL,
  sell_token_price double precision NOT NULL,
  sell_amount numeric(78, 0) NOT NULL,
  buy_amount numeric(78, 0) NOT NULL,
  solver bytea NOT NULL
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

CREATE TABLE IF NOT EXISTS order_executions
(
  order_uid bytea NOT NULL,
  auction_id bigint NOT NULL,
  reward double precision NOT NULL,
  surplus_fee numeric(78, 0) NOT NULL,
  solver_fee numeric(78, 0),

  PRIMARY KEY (order_uid, auction_id)
);

CREATE TYPE PolicyKind AS ENUM ('priceimprovement', 'volume');

CREATE TABLE fee_policies (
  auction_id bigint NOT NULL,
  order_uid bytea NOT NULL,
  -- The order in which the fee policies are inserted and applied.
  application_order SERIAL NOT NULL,
  -- The type of the fee policy.
  kind PolicyKind NOT NULL,
  -- The fee should be taken as a percentage of the price improvement. The value is between 0 and 1.
  price_improvement_factor double precision,
  -- Cap the fee at a certain percentage of the order volume. The value is between 0 and 1.
  max_volume_factor double precision,
  -- The fee should be taken as a percentage of the order volume. The value is between 0 and 1.
  volume_factor double precision,
  PRIMARY KEY (auction_id, order_uid, application_order)
);

TRUNCATE settlements;
TRUNCATE auction_transaction;
TRUNCATE auction_participants;
TRUNCATE settlement_scores;
TRUNCATE settlement_observations;
TRUNCATE auction_prices;
TRUNCATE orders;
TRUNCATE order_quotes;
TRUNCATE trades;
TRUNCATE fee_policies;


INSERT INTO settlements (block_number, log_index, solver, tx_hash, tx_from, tx_nonce)
VALUES (1, 10, '\x5111111111111111111111111111111111111111'::bytea, '\x7111'::bytea, '\x5111111111111111111111111111111111111111'::bytea, 1),
       (2, 10, '\x5222222222222222222222222222222222222222'::bytea, '\x7222'::bytea, '\x5222222222222222222222222222222222222222'::bytea, 1),
       (5, 10, '\x5111111111111111111111111111111111111111'::bytea, '\x7333'::bytea, '\x5111111111111111111111111111111111111111'::bytea, 2),
       -- would the following entry be in the data base? (submitted too late) -- YES
       (20, 10, '\x5111111111111111111111111111111111111111'::bytea, '\x7444'::bytea, '\x5111111111111111111111111111111111111111'::bytea, 3),
       (25, 10, '\x5111111111111111111111111111111111111111'::bytea, '\x7555'::bytea, '\x5111111111111111111111111111111111111111'::bytea, 4),
       (26, 10, '\x5111111111111111111111111111111111111111'::bytea, '\x7666'::bytea, '\x5111111111111111111111111111111111111111'::bytea, 6);

INSERT INTO auction_transaction (auction_id, tx_from, tx_nonce)
VALUES (1, '\x5111111111111111111111111111111111111111'::bytea, 1),
       (2, '\x5222222222222222222222222222222222222222'::bytea, 1),
       (5, '\x5111111111111111111111111111111111111111'::bytea, 2),
       (6, '\x5111111111111111111111111111111111111111'::bytea, 3), -- would that entry be in the data base? (submitted too late)
       (7, '\x5111111111111111111111111111111111111111'::bytea, 4),
       (8, '\x5111111111111111111111111111111111111111'::bytea, 5), -- would that entry be in the data base? (failed transaction)
       (9, '\x5111111111111111111111111111111111111111'::bytea, 6),
       (10, '\x5333333333333333333333333333333333333333'::bytea, 1); -- would that entry be in the data base? (failed transaction)

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


INSERT INTO auction_prices (auction_id, token, price)
VALUES (1, '\x11', 1000000000000000000),
(1, '\x22', 1200000000000000000),
(2, '\x11', 1000000000000000000),
(2, '\x22', 1200000000000000000),
(5, '\x11', 1000000000000000000),
(5, '\x22', 1200000000000000000),
(6, '\x11', 1000000000000000000),
(6, '\x22', 1200000000000000000);

INSERT INTO orders (uid, owner, creation_timestamp, sell_token, buy_token, sell_amount, buy_amount, valid_to, fee_amount, kind, partially_fillable, signature, cancellation_timestamp, receiver, app_data, signing_scheme, settlement_contract, sell_token_balance, buy_token_balance, full_fee_amount, class)
VALUES ('\x1111'::bytea, '\x1111111111'::bytea, '2024-01-01 00:00:00.000000+00
', '\x11'::bytea, '\x22'::bytea, 6000000000000000000, 4000000000000000000, 1700000000, 20000000000000000, 'sell', 'f', '\x987987987987'::bytea, NULL, '\x12341234'::bytea, '\x1234512345'::bytea, 'presign', '\x123456123456'::bytea, 'erc20', 'external', 20000000000000000, 'market'), -- sell market order
('\x2222'::bytea, '\x1111111111'::bytea, '2024-01-01 00:00:00.000000+00
', '\x11'::bytea, '\x22'::bytea, 6000000000000000000, 4000000000000000000, 1700000000, 20000000000000000, 'buy', 'f', '\x987987987987'::bytea, NULL, '\x12341234'::bytea, '\x1234512345'::bytea, 'presign', '\x123456123456'::bytea, 'erc20', 'external', 20000000000000000, 'market'), -- buy market order
('\x3333'::bytea, '\x1111111111'::bytea, '2024-01-01 00:00:00.000000+00
', '\x11'::bytea, '\x22'::bytea, 6020000000000000000, 4000000000000000000, 1700000000, 0, 'sell', 't', '\x987987987987'::bytea, NULL, '\x12341234'::bytea, '\x1234512345'::bytea, 'presign', '\x123456123456'::bytea, 'erc20', 'external', 0, 'limit'), -- partially fillable sell limit order
('\x4444'::bytea, '\x1111111111'::bytea, '2024-01-01 00:00:00.000000+00
', '\x11'::bytea, '\x22'::bytea, 6020000000000000000, 4000000000000000000, 1700000000, 0, 'buy', 't', '\x987987987987'::bytea, NULL, '\x12341234'::bytea, '\x1234512345'::bytea, 'presign', '\x123456123456'::bytea, 'erc20', 'external', 0, 'limit'), -- partially fillable buy limit order
('\x5555'::bytea, '\x1111111111'::bytea, '2024-01-01 00:00:00.000000+00
', '\x11'::bytea, '\x22'::bytea, 6020000000000000000, 4000000000000000000, 1700000000, 0, 'sell', 'f', '\x987987987987'::bytea, NULL, '\x12341234'::bytea, '\x1234512345'::bytea, 'presign', '\x123456123456'::bytea, 'erc20', 'external', 0, 'limit'), -- in market sell limit order
('\x6666'::bytea, '\x1111111111'::bytea, '2024-01-01 00:00:00.000000+00
', '\x11'::bytea, '\x22'::bytea, 6020000000000000000, 4000000000000000000, 1700000000, 0, 'buy', 'f', '\x987987987987'::bytea, NULL, '\x12341234'::bytea, '\x1234512345'::bytea, 'presign', '\x123456123456'::bytea, 'erc20', 'external', 0, 'limit'); -- in market buy limit order

INSERT INTO order_quotes (order_uid, gas_amount, gas_price, sell_token_price, sell_amount, buy_amount, solver)
VALUES ('\x1111'::bytea, 200000, 100000000000, 0.123, 6000000000000000000, 4500000000000000000, '\x5111111111111111111111111111111111111111'::bytea),
('\x2222'::bytea, 200000, 100000000000, 0.123, 5500000000000000000, 4000000000000000000, '\x5333333333333333333333333333333333333333'::bytea),
('\x3333'::bytea, 200000, 100000000000, 0.123, 6000000000000000000, 3000000000000000000, '\x5222222222222222222222222222222222222222'::bytea),
('\x4444'::bytea, 200000, 100000000000, 0.123, 7000000000000000000, 4000000000000000000, '\x5222222222222222222222222222222222222222'::bytea),
('\x5555'::bytea, 200000, 100000000000, 0.123, 6000000000000000000, 4500000000000000000, '\x5333333333333333333333333333333333333333'::bytea),
('\x6666'::bytea, 200000, 100000000000, 0.123, 5500000000000000000, 4000000000000000000, '\x5444444444444444444444444444444444444444'::bytea);

INSERT INTO trades (block_number, log_index, order_uid, sell_amount, buy_amount, fee_amount)
VALUES (1, 0, '\x1111'::bytea, 6020000000000000000, 4600000000000000000, 20000000000000000),
(2, 0, '\x2222'::bytea, 5600000000000000000, 4000000000000000000, 20000000000000000),
(2, 1, '\x3333'::bytea, 6020000000000000000, 4600000000000000000, 0),
(5, 0, '\x4444'::bytea, 5600000000000000000, 4000000000000000000, 0),
(5, 1, '\x5555'::bytea, 6020000000000000000, 4600000000000000000, 0),
(20, 0, '\x6666'::bytea, 5600000000000000000, 4000000000000000000, 0);

INSERT INTO order_executions (order_uid, auction_id, reward, surplus_fee, solver_fee)
VALUES ('\x3333'::bytea, 2, 0, 66464646464646470, NULL),
('\x4444'::bytea, 5, 0, 125000000000000000, NULL),
('\x5555'::bytea, 5, 0, 29043565348022034, NULL),
('\x6666'::bytea, 6, 0, 20000000000000000, NULL);

INSERT INTO fee_policies (auction_id, order_uid, application_order, kind, price_improvement_factor, max_volume_factor, volume_factor)
VALUES (2, '\x3333'::bytea, 3, 'priceimprovement', 0.5, 0.01, NULL),
(5, '\x4444'::bytea, 4, 'priceimprovement', 0.2, 0.1, NULL),
(5, '\x5555'::bytea, 5, 'volume', NULL, NULL, 0.0015),
(6, '\x6666'::bytea, 6, 'priceimprovement', 0.2, 0.1, NULL);
