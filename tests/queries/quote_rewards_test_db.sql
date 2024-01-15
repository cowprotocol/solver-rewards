DROP TABLE IF EXISTS orders;
DROP TYPE IF EXISTS OrderKind;
DROP TABLE IF EXISTS order_quotes;
DROP TABLE IF EXISTS trades;


-- orders table
CREATE TYPE OrderKind AS ENUM ('buy', 'sell');

CREATE TABLE IF NOT EXISTS orders
(
    uid bytea PRIMARY KEY,
    sell_amount numeric(78,0) NOT NULL,
    buy_amount numeric(78,0) NOT NULL,
    fee_amount numeric(78,0) NOT NULL,
    kind OrderKind NOT NULL,
    partially_fillable boolean NOT NULL
);

CREATE TABLE IF NOT EXISTS order_quotes
(
  order_uid bytea PRIMARY KEY,
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


INSERT INTO orders (uid, sell_amount, buy_amount, fee_amount, kind, partially_fillable)
VALUES ('\x01'::bytea, 95000000, 94000000000000000000, 5000000, 'sell', 'f'), -- normal sell market order
('\x02'::bytea, 101000000, 100000000000000000000, 5000000, 'buy', 'f'), -- normal buy market order
('\x03'::bytea, 100000000, 100000000000000000000, 0, 'sell', 't'), -- partially fillable sell limit order
('\x04'::bytea, 100000000, 100000000000000000000, 0, 'buy', 't'), -- partially fillable buy limit order
('\x05'::bytea, 100000000, 94000000000000000000, 0, 'sell', 'f'), -- in market sell limit order
('\x06'::bytea, 106000000, 100000000000000000000, 0, 'buy', 'f'); -- in market buy limit order

INSERT INTO order_quotes (order_uid, sell_amount, buy_amount, solver)
VALUES ('\x01'::bytea, 95000000, 95000000000000000000, '\x01'::bytea),
('\x02'::bytea, 101000000, 100000000000000000000, '\x02'::bytea),
('\x03'::bytea, 100000000, 95000000000000000000, '\x03'::bytea),
('\x04'::bytea, 105000000, 100000000000000000000, '\x03'::bytea),
('\x05'::bytea, 100000000, 95000000000000000000, '\x03'::bytea),
('\x06'::bytea, 105000000, 100000000000000000000, '\x03'::bytea);

INSERT INTO trades (block_number, log_index, order_uid, sell_amount, buy_amount)
VALUES (1, 0, '\x01'::bytea, 100000000, 95000000000000000000),
(2, 0, '\x02'::bytea, 106000000, 100000000000000000000),
(3, 0, '\x03'::bytea, 100000000, 101000000000000000000),
(4, 0, '\x04'::bytea, 99000000, 100000000000000000000),
(5, 0, '\x05'::bytea, 100000000, 95000000000000000000),
(6, 0, '\x06'::bytea, 105000000, 100000000000000000000);
