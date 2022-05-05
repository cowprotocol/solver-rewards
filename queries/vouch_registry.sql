with valid_tokens as (
  select *
  from erc20.tokens
  where contract_address in (
      '\xDEf1CA1fb7FBcDC777520aa7f396b4E015F497aB', -- COW Token
      '\x39AA39c021dfbaE8faC545936693aC917d5E7563' -- cUSDC
    )
),
-- Bonding Pool Addresses
-- Gnosis: 0x8353713b6D2F728Ed763a04B886B16aAD2b16eBD
-- CoW Services: 0x5d4020b9261F01B6f8a45db929704b0Ad6F5e9E6
recognized_bonding_pools (pool, name) as (
  SELECT *
  from (
      values (
          replace('0x8353713b6D2F728Ed763a04B886B16aAD2b16eBD', '0x', '\x')::bytea,
          'Gnosis'
        ),
        (
          replace('0x5d4020b9261F01B6f8a45db929704b0Ad6F5e9E6', '0x', '\x')::bytea,
          'CoW Services'
        )
    ) as _
),
-- TODO: Make initial funders front-running resistant.
--       This would involve detecting the magnitude of the deposits 
--       and choosing the first sender with "substantial" deposit
initial_funders as (
  select name,
    pool,
    (
      select "from"
      from erc20."ERC20_evt_Transfer"
      where "to" = pool
        and contract_address in (
          select contract_address
          from valid_tokens
        )
      order by evt_block_number,
        evt_index
      limit 1
    ) as initial_funder,
    case
      when (
        select count(distinct "from")
        from erc20."ERC20_evt_Transfer"
        where "to" = pool
          and contract_address in (
            select contract_address
            from valid_tokens
          )
      ) = 1 then True
      else False
    end as unique_depositor
  from recognized_bonding_pools
),
vouches as (
  select evt_block_time,
    evt_index,
    solver,
    "cowRewardTarget" as reward_target,
    pool,
    sender,
    True as active
  from cow_protocol."VouchRegister_evt_Vouch"
    join initial_funders on pool = "bondingPool"
    and sender = initial_funder
),
invalidations as (
  select evt_block_time,
    evt_index,
    solver,
    Null::bytea as reward_target,
    pool,
    sender,
    False as active
  from cow_protocol."VouchRegister_evt_InvalidateVouch"
    join initial_funders on pool = "bondingPool"
    and sender = initial_funder
),
-- At this point we have excluded all arbitrary vouches (i.e. those not from initial funders of recognized pools)
-- This ranks (solver, pool, sender) by most recent (vouch or invalidation) 
-- and yields as rank 1, the current "active" status of the triplet.
ranked_vouches as (
  select rank() over (
      partition by solver,
      pool,
      sender
      order by evt_block_time desc,
        evt_index desc
    ) as rk,
    *
  from (
      select *
      from vouches
      union
      select *
      from invalidations
    ) as _
),
-- This will contain all latest active vouches,
-- but could still contain solvers with multiplicity > 1 for different pools.
-- Rank here again by solver, and time.
current_active_vouches as (
  select rank() over (
      partition by solver
      order by evt_block_time,
        evt_index
    ) as time_rank,
    *
  from ranked_vouches
  where rk = 1
    and active = True
),
-- To filter for the case of "same solver, different pool",
-- rank the current_active vouches and choose the earliest
valid_vouches as (
  select solver,
    reward_target,
    pool
  from current_active_vouches
  where time_rank = 1
)
select *
from valid_vouches
