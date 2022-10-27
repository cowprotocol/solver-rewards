-- https://dune.com/queries/1468170
select
  tx_hash,
  amount,
  safe_liquidity,
  case
    when amount > 0
    and safe_liquidity = True then 37.0
    else amount
  end as adjusted_amount
from
  dune_user_generated.cow_per_order_rewards_{{PeriodHash}}
where
  solver = '{{SolverAddress}}'