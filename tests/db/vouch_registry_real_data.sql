-- select * from cow_protocol."VouchRegister_evt_InvalidateVouch"
-- select * from cow_protocol."VouchRegister_evt_Vouch"


-- select * from (
--     select evt_block_number as "number", evt_block_time as time
--     from cow_protocol."VouchRegister_evt_Vouch"
--     union
--     select evt_block_number as "number", evt_block_time as time
--     from cow_protocol."VouchRegister_evt_InvalidateVouch"
-- ) as _


-- REAL DATA TEST

TRUNCATE cow_protocol."VouchRegister_evt_InvalidateVouch";
TRUNCATE cow_protocol."VouchRegister_evt_Vouch";
TRUNCATE ethereum.blocks;


COPY cow_protocol."VouchRegister_evt_Vouch"(solver,"bondingPool","cowRewardTarget",sender,contract_address,evt_tx_hash,evt_index,evt_block_time,evt_block_number)
FROM '/repo/tests/data/cow_protocol.VouchRegister_evt_Vouch.csv'
DELIMITER ','
CSV HEADER;

COPY cow_protocol."VouchRegister_evt_InvalidateVouch"(solver,"bondingPool",sender,contract_address,evt_tx_hash,evt_index,evt_block_time,evt_block_number)
FROM '/repo/tests/data/cow_protocol.VouchRegister_evt_InvalidateVouch.csv'
DELIMITER ','
CSV HEADER;

COPY ethereum.blocks("number", time)
FROM '/repo/tests/data/ethereum.blocks.csv'
DELIMITER ','
CSV HEADER;
