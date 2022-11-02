-- Table aggregating all the pages must be dropped in order to replace the pages.
DROP VIEW IF EXISTS dune_user_generated.cow_order_rewards_{{Environment}};
-- This is only temporary because of schema change.
-- DROP VIEW IF EXISTS dune_user_generated.{{TableName}};
CREATE OR REPLACE VIEW dune_user_generated.{{TableName}} (
    order_uid,
    solver,
    tx_hash,
    amount,
    safe_liquidity
) AS (
    select
        order_uid::bytea,
        solver::bytea,
        tx_hash::bytea,
        amount::numeric,
        safe_liquidity::bool
    from (VALUES
{{Values}}
    ) as _ (order_uid, solver, tx_hash, amount, safe_liquidity)
);
