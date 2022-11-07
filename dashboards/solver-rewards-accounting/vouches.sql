select
    concat('0x', encode(reward_target, 'hex')) as reward_target,
    concat('0x', encode(vv.pool, 'hex')) as bonding_pool,
    bp.name as pool_name,
    count(*) as num_solvers,
    array_agg(distinct s.name) as solver_names,
    array_agg(concat('0x', encode(solver, 'hex'))) as solver_addresses
from valid_vouches vv
join gnosis_protocol_v2."view_solvers" s
    on address = solver
join bonding_pools bp
    on vv.pool = bp.pool
group by reward_target, bonding_pool, pool_name