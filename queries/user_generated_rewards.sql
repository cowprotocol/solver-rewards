DROP MATERIALIZED VIEW IF EXISTS dune_user_generated.cow_rewards_{{PeriodHash}} CASCADE;
CREATE MATERIALIZED VIEW dune_user_generated.cow_rewards_{{PeriodHash}} (solver, num_trades, cow_reward) AS (
  SELECT *
  FROM (
      VALUES
{{SolverRewards}}
    ) as _
);
SELECT * FROM dune_user_generated.cow_rewards_{{PeriodHash}}