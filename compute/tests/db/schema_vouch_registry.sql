
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

-- We can either have this during setUp (uncommented) or manually during tearDown
TRUNCATE cow_protocol."VouchRegister_evt_Vouch";
TRUNCATE cow_protocol."VouchRegister_evt_InvalidateVouch";
TRUNCATE ethereum.blocks;

-- This is a bit dirty, but basically just needs to contain all the block numbers used in the tests.
INSERT INTO ethereum.blocks VALUES (0, '1970-01-01'), (1, '1971-01-01'), (2, '1972-01-01'), (3, '1973-01-01');