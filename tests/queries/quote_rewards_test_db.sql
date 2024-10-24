DROP TABLE IF EXISTS orders;
DROP TABLE IF EXISTS jit_orders;
DROP TYPE IF EXISTS OrderKind;
DROP TYPE IF EXISTS OrderClass;
DROP TABLE IF EXISTS order_quotes;
DROP TABLE IF EXISTS trades;


-- orders table
CREATE TYPE OrderKind AS ENUM ('buy', 'sell');
CREATE TYPE OrderClass AS ENUM ('limit');

CREATE TABLE IF NOT EXISTS orders
(
    uid bytea PRIMARY KEY,
    sell_amount numeric(78,0) NOT NULL,
    buy_amount numeric(78,0) NOT NULL,
    fee_amount numeric(78,0) NOT NULL,
    kind OrderKind NOT NULL,
    partially_fillable boolean NOT NULL,
    class OrderClass NOT NULL
);

CREATE TABLE IF NOT EXISTS order_quotes
(
  order_uid bytea PRIMARY KEY,
  gas_amount numeric(78, 0) NOT NULL,
  gas_price numeric(78, 0) NOT NULL,
  sell_token_price float NOT NULL,
  sell_amount numeric(78, 0) NOT NULL,
  buy_amount numeric(78, 0) NOT NULL,
  solver bytea NOT NULL
);

CREATE TABLE IF NOT EXISTS trades
(
  block_number bigint NOT NULL,
  log_index bigint NOT NULL,
  order_uid bytea NOT NULL,
  sell_amount numeric(78, 0) NOT NULL,
  buy_amount numeric(78, 0) NOT NULL,

  PRIMARY KEY (block_number, log_index)
);


TRUNCATE orders;
TRUNCATE order_quotes;
TRUNCATE trades;


INSERT INTO orders (uid, sell_amount, buy_amount, fee_amount, kind, partially_fillable, class)
VALUES ('\x03'::bytea, 100000000, 100000000000000000000, 0, 'sell', 't', 'limit'), -- partially fillable sell limit order
('\x04'::bytea, 100000000, 100000000000000000000, 0, 'buy', 't', 'limit'), -- partially fillable buy limit order
('\x05'::bytea, 100000000, 94000000000000000000, 0, 'sell', 'f', 'limit'), -- in market sell limit order
('\x06'::bytea, 106000000, 100000000000000000000, 0, 'buy', 'f', 'limit'); -- in market buy limit order

INSERT INTO order_quotes (order_uid, gas_amount, gas_price, sell_token_price, sell_amount, buy_amount, solver)
VALUES ('\x03'::bytea, 100000, 25000000000, 500000000., 100000000, 100000000000000000000, '\x03'::bytea),
('\x04'::bytea, 100000, 25000000000, 500000000., 100000000, 100000000000000000000, '\x03'::bytea),
('\x05'::bytea, 100000, 25000000000, 500000000., 100000000, 100000000000000000000, '\x03'::bytea),
('\x06'::bytea, 100000, 25000000000, 500000000., 100000000, 100000000000000000000, '\x03'::bytea);

INSERT INTO trades (block_number, log_index, order_uid, sell_amount, buy_amount)
VALUES  (3, 0, '\x03'::bytea, 100000000, 101000000000000000000),
(4, 0, '\x04'::bytea, 99000000, 100000000000000000000),
(5, 0, '\x05'::bytea, 100000000, 95000000000000000000),
(6, 0, '\x06'::bytea, 105000000, 100000000000000000000);
