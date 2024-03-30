-- https://github.com/cowprotocol/solver-rewards/pull/330
-- V3: https://dune.com/queries/3333356
select
    min("number") as start_block,
    max("number") as end_block
from ethereum.blocks
where time >= cast('{{StartTime}}' as timestamp) and time < cast('{{EndTime}}' as timestamp)