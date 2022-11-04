select order_uid::bytea,
       solver::bytea,
       tx_hash::bytea,
       amount::numeric,
       safe_liquidity::bool
from (VALUES
{{Values}}
) as _ (order_uid, solver, tx_hash, amount, safe_liquidity)