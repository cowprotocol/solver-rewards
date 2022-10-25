DROP MATERIALIZED VIEW IF EXISTS dune_user_generated.cow_per_order_rewards_{{PeriodHash}} CASCADE;
CREATE MATERIALIZED VIEW dune_user_generated.cow_per_order_rewards_{{PeriodHash}} (solver, tx_hash, amount, safe_liquidity) AS (
  SELECT *
  FROM (
      VALUES
{{SolverRewards}}
    ) as _
);
SELECT * FROM dune_user_generated.cow_per_order_rewards_{{PeriodHash}}