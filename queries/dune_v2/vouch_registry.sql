-- -- V2 Query: https://dune.com/queries/1541516
with
bonding_pools (pool, name, initial_funder) as (
  select lower(pool), name, lower(funder) from (
    values {{BondingPoolData}}
  ) as _ (pool, name, funder)
),

last_block_before_timestamp as (
    select max(number) from ethereum.blocks
    where time < '{{EndTime}}'
),

-- Query Logic Begins here!
vouches as (
  select
    evt_block_number,
    evt_index,
    solver,
    cowRewardTarget as reward_target,
    pool,
    sender,
    True as active
  from cow_protocol_ethereum.VouchRegister_evt_Vouch
    join bonding_pools
        on pool = bondingPool
        and sender = initial_funder
  where evt_block_number <= (select * from last_block_before_timestamp)
),
invalidations as (
  select
    evt_block_number,
    evt_index,
    solver,
    Null as reward_target,  -- This is just ot align with vouches to take a union
    pool,
    sender,
    False as active
  from cow_protocol_ethereum.VouchRegister_evt_InvalidateVouch
    join bonding_pools
        on pool = bondingPool
        and sender = initial_funder
  where evt_block_number <= (select * from last_block_before_timestamp)
),
-- At this point we have excluded all arbitrary vouches (i.e. those not from initial funders of recognized pools)
-- This ranks (solver, pool, sender) by most recent (vouch or invalidation)
-- and yields as rank 1, the current "active" status of the triplet.
ranked_vouches as (
  select rank() over (
      partition by solver, pool, sender
      order by evt_block_number desc, evt_index desc
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
      order by evt_block_number, evt_index
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
),
complete_results as (
    select
        solver,
        concat(environment, '-', s.name) as solver_name,
        reward_target,
        vv.pool as bonding_pool,
        bp.name as pool_name
    from valid_vouches vv
    join cow_protocol_ethereum.solvers s
        on address = solver
    join bonding_pools bp
        on vv.pool = bp.pool
)

select * from {{VOUCH_CTE_NAME}}

