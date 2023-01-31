-- V2: https://dune.com/queries/1541504
select min(number) as start_block,
       max(number) as end_block
from ethereum.blocks
where time between '{{StartTime}}' and '{{EndTime}}'