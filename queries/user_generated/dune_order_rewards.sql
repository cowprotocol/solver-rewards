-- https://dune.com/queries/1476356
CREATE OR REPLACE VIEW dune_user_generated.cow_order_rewards_{{Environment}} (
    page,
    order_uid,
    solver,
    tx_hash,
    amount,
    safe_liquidity
) AS (
{{Values}}
);
