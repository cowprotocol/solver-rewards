-- https://dune.com/queries/1468170
select
  tx_hash,
  amount,
  safe_liquidity
from
  dune_user_generated.cow_per_order_rewards_{{PeriodHash}}
where
  solver = '{{SolverAddress}}'