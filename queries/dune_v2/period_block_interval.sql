-- V3: https://dune.com/queries/1541504
select
    min("number") as start_block,
    max("number") as end_block
from ethereum.blocks
where date_trunc('minute', time) between cast('{{StartTime}}' as timestamp) and cast('{{EndTime}}' as timestamp)
