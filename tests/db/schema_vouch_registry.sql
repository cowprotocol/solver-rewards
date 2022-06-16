
CREATE SCHEMA IF NOT EXISTS ethereum;
CREATE SCHEMA IF NOT EXISTS cow_protocol;

-- These are the only fields we need from blocks.
CREATE TABLE IF NOT EXISTS ethereum.blocks (
   "number" numeric UNIQUE,
   time timstamptz
);

CREATE TABLE IF NOT EXISTS cow_protocol."VouchRegister_evt_Vouch" (
   solver bytea NOT NULL,
   "bondingPool" bytea NOT NULL,
   "cowRewardTarget" bytea NOT NULL,
   sender bytea NOT NULL,
   contract_address bytea NOT NULL,
   evt_tx_hash bytea NOT NULL,
   evt_index int8 NOT NULL,
   evt_block_time timestamptz NOT NULL,
   evt_block_number int8 NOT NULL
);

CREATE TABLE IF NOT EXISTS cow_protocol."VouchRegister_evt_InvalidateVouch" (
   solver bytea NOT NULL,
   "bondingPool" bytea NOT NULL,
   sender bytea NOT NULL,
   contract_address bytea NOT NULL,
   evt_tx_hash bytea NOT NULL,
   evt_index int8 NOT NULL,
   evt_block_time timestamptz NOT NULL,
   evt_block_number int8 NOT NULL
);