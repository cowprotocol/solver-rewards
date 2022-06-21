
-- Fetch CSV Data: (python script)
-- TODO: Should parameterize the fetch csv data {{StartTime}}, {{EndTime}}

-- select * from erc20.tokens

-- select * from erc20."ERC20_evt_Transfer"
-- WHERE '\x9008D19f58AAbD9eD0D60971565AA8510560ab41' in ("to", "from")
-- and evt_block_time between '2022-03-01' and '2022-03-11'

-- with
-- token_times as (
--     select
--         date_trunc('hour', evt_block_time) as hour,
--         date_trunc('minute', evt_block_time) as minute,
--         contract_address
--     from erc20."ERC20_evt_Transfer"
--     where '\x9008D19f58AAbD9eD0D60971565AA8510560ab41' in ("to", "from")
--     and evt_block_time between '2022-03-01' and '2022-03-11'
--     group by hour, minute, contract_address
-- )

-- -- prices.usd
-- select pusd.* from prices.usd pusd
-- inner join token_times tt
-- on pusd.minute = tt.minute
-- and pusd.contract_address = tt.contract_address

-- -- prices_from_dex_data
-- select p.* from prices.prices_from_dex_data p
-- inner join token_times tt
-- on p.hour = tt.hour
-- and p.contract_address = tt.contract_address

-- select * from prices.layer1_usd_eth
-- where minute between '2022-03-01' and '2022-03-11'

-- select * from gnosis_protocol_v2."trades"
-- where block_time between '2022-03-01' and '2022-03-11'

-- select * from gnosis_protocol_v2."batches"
-- where block_time between '2022-03-01' and '2022-03-11'

-- $ docker cp ./csvs/ postgres_container:/


-- Create Schemas:
CREATE SCHEMA IF NOT EXISTS erc20;
CREATE SCHEMA IF NOT EXISTS prices;
CREATE SCHEMA IF NOT EXISTS gnosis_protocol_v2;
CREATE SCHEMA IF NOT EXISTS dune_user_generated;
CREATE SCHEMA IF NOT EXISTS ethereum;
CREATE SCHEMA IF NOT EXISTS cow_protocol;

-- These are the only fields we need from blocks.
CREATE TABLE IF NOT EXISTS ethereum.blocks (
   "number" numeric UNIQUE,
   time timestamptz
);

CREATE TABLE IF NOT EXISTS cow_protocol."VouchRegister_evt_Vouch" (
   solver bytea NOT NULL,
   "bondingPool" bytea NOT NULL,
   "cowRewardTarget" bytea NOT NULL,
   sender bytea NOT NULL,
   evt_index int8 NOT NULL,
   evt_block_number int8 NOT NULL,
   -- This columns are irrelevant for testing
   contract_address bytea,
   evt_tx_hash bytea,
   evt_block_time timestamptz
);

CREATE TABLE IF NOT EXISTS cow_protocol."VouchRegister_evt_InvalidateVouch" (
   solver bytea NOT NULL,
   "bondingPool" bytea NOT NULL,
   sender bytea NOT NULL,
   evt_index int8 NOT NULL,
   evt_block_number int8 NOT NULL,
   -- This columns are irrelevant for testing
   contract_address bytea,
   evt_tx_hash bytea,
   evt_block_time timestamptz
);


-- Schemas for each table were defined from dune more or less as follows:
-- select
--     column_name,
--     data_type,
--     is_nullable
-- from information_schema.columns
-- where table_schema = 'prices'
-- and table_name = 'usd';

-- Create Tables

-- Tokens:
CREATE TABLE IF NOT EXISTS erc20.tokens (
   contract_address bytea UNIQUE,
   symbol text,
   decimals integer
);
CREATE INDEX IF NOT EXISTS tokens_contract_address_decimals_idx ON erc20.tokens USING btree (contract_address) INCLUDE (decimals);
CREATE INDEX IF NOT EXISTS tokens_symbol_decimals_idx ON erc20.tokens USING btree (symbol) INCLUDE (decimals);

CREATE TABLE IF NOT EXISTS erc20."ERC20_evt_Transfer" (
   "from" bytea,
   "to" bytea,
   value numeric,
   contract_address bytea not NULL,
   evt_tx_hash bytea not NULL,
   evt_index bigint not NULL,
   evt_block_time timestamptz not NULL,
   evt_block_number bigint not NULL
);

-- Prices:
CREATE TABLE IF NOT EXISTS prices.usd (
   minute timestamptz not NULL,
   price double precision not NULL,
   decimals smallint not NULL,
   contract_address bytea not NULL,
   symbol text not NULL
);
CREATE TABLE IF NOT EXISTS prices.layer1_usd_eth (
   minute timestamptz not NULL,
   price double precision not NULL,
   symbol text not NULL
);
CREATE TABLE IF NOT EXISTS prices.prices_from_dex_data (
   contract_address bytea not NULL,
   hour timestamptz not NULL,
   median_price numeric,
   sample_size integer,
   symbol text,
   decimals smallint
);

-- Protocol

-- Batches:
CREATE TABLE IF NOT EXISTS gnosis_protocol_v2.batches
(
    block_time      timestamptz NOT NULL,
    num_trades      int8        NOT NULL,
    dex_swaps       int8        NOT NULL,
    batch_value     numeric,
    gas_per_trade   numeric,
    solver_address  bytea       NOT NULL,
    solver_name     text,
    tx_hash         bytea       NOT NULL,
    gas_price_gwei  float8,
    gas_used        numeric,
    tx_cost_usd     numeric,
    fee_value       numeric,
    call_data_size  numeric,
    unwraps         int8,
    token_approvals int8
);

CREATE UNIQUE INDEX IF NOT EXISTS batches_id ON gnosis_protocol_v2.batches (tx_hash);
CREATE INDEX IF NOT EXISTS batches_idx_1 ON gnosis_protocol_v2.batches (block_time);
CREATE INDEX IF NOT EXISTS batches_idx_2 ON gnosis_protocol_v2.batches (solver_address);
CREATE INDEX IF NOT EXISTS batches_idx_3 ON gnosis_protocol_v2.batches (num_trades);


-- Trades
CREATE TABLE IF NOT EXISTS gnosis_protocol_v2.trades
(
    app_data           text,
    atoms_bought       numeric     NOT NULL,
    atoms_sold         numeric     NOT NULL,
    block_time         timestamptz NOT NULL,
    buy_price          numeric,
    buy_token_address  bytea       NOT NULL,
    buy_token          text,
    buy_value_usd      numeric,
    fee                numeric,
    fee_atoms          numeric     NOT NULL,
    fee_usd            numeric,
    order_uid          bytea       NOT NULL,
    receiver           bytea,
    sell_price         numeric,
    sell_token_address bytea       NOT NULL,
    sell_token         text,
    sell_value_usd     numeric,
    trader             bytea       NOT NULL,
    trade_value_usd    numeric,
    tx_hash            bytea       NOT NULL,
    units_bought       numeric,
    units_sold         numeric
);

CREATE UNIQUE INDEX IF NOT EXISTS trades_id ON gnosis_protocol_v2.trades (order_uid, tx_hash);
CREATE INDEX IF NOT EXISTS trades_idx_1 ON gnosis_protocol_v2.trades (block_time);
CREATE INDEX IF NOT EXISTS trades_idx_2 ON gnosis_protocol_v2.trades (sell_token_address);
CREATE INDEX IF NOT EXISTS trades_idx_3 ON gnosis_protocol_v2.trades (buy_token_address);
CREATE INDEX IF NOT EXISTS trades_idx_4 ON gnosis_protocol_v2.trades (trader);
CREATE INDEX IF NOT EXISTS trades_idx_5 ON gnosis_protocol_v2.trades (app_data);
CREATE INDEX IF NOT EXISTS trades_idx_6 ON gnosis_protocol_v2.trades (tx_hash);

-- Solvers
CREATE TABLE IF NOT EXISTS gnosis_protocol_v2.view_solvers (
   address bytea NOT NULL,
   environment text NOT NULL,
   name text NOT NULL,
   active bool NOT NULL
);

CREATE TABLE IF NOT EXISTS gnosis_protocol_v2."GPv2Settlement_call_settle" (
    call_block_number bigint NOT NULL,
    call_block_time timestamptz NOT NULL,
    call_success boolean NOT NULL,
    call_tx_hash bytea NOT NULL,
    "clearingPrices" numeric[],
    contract_address bytea NOT NULL,
    tokens bytea[]
);

CREATE TABLE IF NOT EXISTS dune_user_generated.cow_trusted_tokens (
    address bytea NOT NULL
);

TRUNCATE erc20.tokens;
TRUNCATE erc20."ERC20_evt_Transfer";

TRUNCATE prices.usd;
TRUNCATE prices.prices_from_dex_data;
TRUNCATE prices.layer1_usd_eth;

TRUNCATE gnosis_protocol_v2.trades;
TRUNCATE gnosis_protocol_v2.batches;
TRUNCATE gnosis_protocol_v2.view_solvers;
TRUNCATE gnosis_protocol_v2."GPv2Settlement_call_settle";

TRUNCATE dune_user_generated.cow_trusted_tokens;

TRUNCATE cow_protocol."VouchRegister_evt_Vouch";
TRUNCATE cow_protocol."VouchRegister_evt_InvalidateVouch";

TRUNCATE ethereum.blocks;

-- Copy CSV data into tables
COPY erc20.tokens(contract_address, symbol, decimals)
FROM '/repo/tests/data/erc20.tokens.csv'
DELIMITER ','
CSV HEADER;


COPY erc20."ERC20_evt_Transfer"
FROM '/repo/tests/data/erc20.ERC20_evt_Transfer.csv'
DELIMITER ','
CSV HEADER;

COPY prices.usd
FROM '/repo/tests/data/prices.usd.csv'
DELIMITER ','
CSV HEADER;

COPY prices.prices_from_dex_data
FROM '/repo/tests/data/prices.prices_from_dex_data.csv'
DELIMITER ','
CSV HEADER;

COPY prices.layer1_usd_eth
FROM '/repo/tests/data/prices.layer1_usd_eth.csv'
DELIMITER ','
CSV HEADER;


COPY gnosis_protocol_v2.trades
FROM '/repo/tests/data/gnosis_protocol_v2.trades.csv'
DELIMITER ','
CSV HEADER;

COPY gnosis_protocol_v2.batches
FROM '/repo/tests/data/gnosis_protocol_v2.batches.csv'
DELIMITER ','
CSV HEADER;

COPY gnosis_protocol_v2.view_solvers
FROM '/repo/tests/data/gnosis_protocol_v2.view_solvers.csv'
DELIMITER ','
CSV HEADER;

COPY gnosis_protocol_v2."GPv2Settlement_call_settle"
FROM '/repo/tests/data/gnosis_protocol_v2.GPv2Settlement_call_settle.csv'
DELIMITER ','
CSV HEADER;

COPY dune_user_generated.cow_trusted_tokens
FROM '/repo/tests/data/dune_user_generated.cow_trusted_tokens.csv'
DELIMITER ','
CSV HEADER;

-- This is a bit dirty, but basically just needs to contain all the block numbers used in the tests.
INSERT INTO ethereum.blocks VALUES (0, '1970-01-01'), (1, '1971-01-01'), (2, '1972-01-01'), (3, '1973-01-01');
