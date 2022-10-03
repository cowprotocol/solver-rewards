-- Permanent version here: https://dune.com/queries/1328116
select min("number") as start_block,
       max("number") as end_block
from ethereum.blocks
where time between '{{StartTime}}' and '{{EndTime}}'