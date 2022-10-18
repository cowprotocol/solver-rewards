DROP MATERIALIZED VIEW IF EXISTS dune_user_generated.cow_rewards_{{AccountingPeriodHash}} CASCADE;
CREATE MATERIALIZED VIEW dune_user_generated.cow_rewards_{{AccountingPeriodHash}} (solver, num_trades, cow_reward) AS (
  SELECT *
  FROM (
      VALUES
{{SolverRewards}}
    ) as _
);
SELECT * FROM dune_user_generated.cow_rewards_{{AccountingPeriodHash}}