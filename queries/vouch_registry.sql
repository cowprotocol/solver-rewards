with
-- Find permanent version of this query at: https://dune.com/queries/674947
-- Contract events queried here are from the VouchRegister verified at
-- https://etherscan.io/address/0xb422f2520b0b7fd86f7da61b32cc631a59ed7e8f#code
test_bonding_pools (pool, name, initial_funder) as (
  select *
  from (
    values
        ('\xb0'::bytea, 'Pool 0', '\xf0'::bytea),
        ('\xb1'::bytea, 'Pool 1', '\xf1'::bytea),
        ('\xb2'::bytea, 'Pool 2', '\xf2'::bytea),
        ('\xb3'::bytea, 'Pool 3', '\xf3'::bytea),
        ('\xb4'::bytea, 'Pool 4', '\xf4'::bytea),
        ('\xb5'::bytea, 'Pool 5', '\xf5'::bytea)
    ) as _
),
test_vouch_events (evt_block_number, evt_index, solver, "cowRewardTarget", "bondingPool", sender) as (
    select * from (
        values
            -- Test Case 0: vouch for same solver, two different pools then invalidate the first
            (0, 0, '\x50'::bytea, '\xc1'::bytea, '\xb0'::bytea, '\xf0'::bytea), -- vouch(solver0, pool0)
            (1, 0, '\x50'::bytea, '\xc1'::bytea, '\xb1'::bytea, '\xf1'::bytea),  -- vouch(solver0, pool1)
            -- Test Case 1: Invalidation before Vouch
            (1, 0, '\x51'::bytea, '\xc1'::bytea, '\xb0'::bytea, '\xf0'::bytea),  -- vouch(solver1, pool0)
            -- Test Case 2: Vouch with wrong sender
            (1, 0, '\x52'::bytea, '\xc1'::bytea, '\xb0'::bytea, '\xf1'::bytea),  -- vouch(solver2, pool0, sender1)
            -- Test Case 3: Valid Vouch
            (1, 0, '\x53'::bytea, '\xc1'::bytea, '\xb2'::bytea, '\xf2'::bytea),  -- vouch(solver3, pool2, sender2)
            -- Test Case 4: Update Cow Reward Target
            (1, 0, '\x54'::bytea, '\xc1'::bytea, '\xb2'::bytea, '\xf2'::bytea),  -- vouch(solver4, pool2, reward_target1)
            (1, 1, '\x54'::bytea, '\xc2'::bytea, '\xb2'::bytea, '\xf2'::bytea),  -- vouch(solver4, pool2, reward_target2)
            (2, 0, '\x54'::bytea, '\xc3'::bytea, '\xb2'::bytea, '\xf2'::bytea),  -- vouch(solver4, pool2, reward_target3)
            -- Last dummy Row
            (99999, 0, '\xff'::bytea, '\xff'::bytea, '\xff'::bytea, '\xff'::bytea)
    ) as _
),
test_invalidation_events (evt_block_number, evt_index, solver, "bondingPool", sender) as (
    select * from (
        values
            -- Test Case 0: vouch for same solver, two different pools then invalidate the first
            (3, 0, '\x50'::bytea, '\xb0'::bytea, '\xf0'::bytea), -- invalidate(solver0, pool0)
            -- Test Case 1: Invalidation before Vouch
            (0, 0, '\x51'::bytea, '\xb0'::bytea, '\xf0'::bytea), -- invalidate(solver1, pool0)
            -- Last dummy Row: here so that we can comment out the above entries
            (99999, 0, '\xff'::bytea, '\xff'::bytea, '\xff'::bytea)
    ) as _
),
real_bonding_pools (pool, name, initial_funder) as (
  select *
  from (
    values
        ('\x8353713b6D2F728Ed763a04B886B16aAD2b16eBD'::bytea, 'Gnosis', '\x6c642cafcbd9d8383250bb25f67ae409147f78b2'::bytea),
        ('\x5d4020b9261F01B6f8a45db929704b0Ad6F5e9E6'::bytea, 'CoW Services', '\x423cec87f19f0778f549846e0801ee267a917935'::bytea)
    ) as _
),
real_vouch_events as (
    select evt_block_number, evt_index, solver, "cowRewardTarget", "bondingPool", sender
    from cow_protocol."VouchRegister_evt_Vouch"
),
real_invalidation_events as (
    select evt_block_number, evt_index, solver, "bondingPool", sender
    from cow_protocol."VouchRegister_evt_InvalidateVouch"
),

-- Query Logic Begins here!
vouches as (
  select
    evt_block_number,
    evt_index,
    solver,
    "cowRewardTarget" as reward_target,
    pool,
    sender,
    True as active
  from {{Scenario}}_vouch_events
    join {{Scenario}}_bonding_pools
        on pool = "bondingPool"
        and sender = initial_funder
),
invalidations as (
  select
    evt_block_number,
    evt_index,
    solver,
    Null::bytea as reward_target,  -- This is just ot align with vouches to take a union
    pool,
    sender,
    False as active
  from {{Scenario}}_invalidation_events
    join {{Scenario}}_bonding_pools
        on pool = "bondingPool"
        and sender = initial_funder
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
)
select *
from valid_vouches
