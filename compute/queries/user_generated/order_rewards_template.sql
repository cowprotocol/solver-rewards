select order_uid::bytea,
       solver::bytea,
       tx_hash::bytea,
       surplus_fee::numeric,
       amount::numeric
from (VALUES
{{Values}}
) as _ (order_uid, solver, tx_hash, surplus_fee, amount)