-- V3: https://dune.com/queries/3333356
with
  block_range_start as (
    select
      max("number") + 1 as start_block
    from
      ethereum.blocks
    where
      time <= cast('{{StartTime}}' as timestamp)
  ),
  block_range_stop as (
    select
      max("number") as end_block
    from
      ethereum.blocks
    where
      time <= cast('{{EndTime}}' as timestamp)
  )
select
  *
from
  block_range_start
  cross join block_range_stop