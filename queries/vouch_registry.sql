with
-- Find permanent version of this query at: https://dune.com/queries/674947
-- Contract events queried here are from the VouchRegister verified at
-- https://etherscan.io/address/0xb422f2520b0b7fd86f7da61b32cc631a59ed7e8f#code
recognized_bonding_pools (pool, name, initial_funder) as (
  select *
  from (
    values
        -- This Pool has not yet been funded.
        -- ('\x8353713b6D2F728Ed763a04B886B16aAD2b16eBD'::bytea, 'Gnosis'),
        ('\x5d4020b9261F01B6f8a45db929704b0Ad6F5e9E6'::bytea, 'CoW Services', '\x423cec87f19f0778f549846e0801ee267a917935'::bytea)
    ) as _
),
vouches as (
  select
    evt_block_time,
    evt_index,
    solver,
    "cowRewardTarget" as reward_target,
    pool,
    sender,
    True as active
  from cow_protocol."VouchRegister_evt_Vouch"
    join recognized_bonding_pools
        on pool = "bondingPool"
        and sender = initial_funder
),
invalidations as (
  select
    evt_block_time,
    evt_index,
    solver,
    Null::bytea as reward_target,  -- This is just ot align with vouches to take a union
    pool,
    sender,
    False as active
  from cow_protocol."VouchRegister_evt_InvalidateVouch"
    join recognized_bonding_pools
        on pool = "bondingPool"
        and sender = initial_funder
),
-- At this point we have excluded all arbitrary vouches (i.e. those not from initial funders of recognized pools)
-- This ranks (solver, pool, sender) by most recent (vouch or invalidation) 
-- and yields as rank 1, the current "active" status of the triplet.
ranked_vouches as (
  select rank() over (
      partition by solver, pool, sender
      order by evt_block_time desc, evt_index desc
    ) as rk,
    *
  from (
      select * from vouches
      union
      select * from invalidations
    ) as _
),
-- This will contain all latest active vouches,
-- but could still contain solvers with multiplicity > 1 for different pools.
-- Rank here again by solver, and time.
current_active_vouches as (
  select rank() over (
      partition by solver
      order by evt_block_time, evt_index
    ) as time_rank,
    *
  from ranked_vouches
  where rk = 1
    and active = True
),
-- To filter for the case of "same solver, different pool",
-- rank the current_active vouches and choose the earliest
valid_vouches as (
  select
    solver,
    reward_target,
    pool
  from current_active_vouches
  where time_rank = 1
)
select *
from valid_vouches
