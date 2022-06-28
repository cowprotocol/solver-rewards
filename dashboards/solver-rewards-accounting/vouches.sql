select
 concat('0x', encode(solver, 'hex')) as solver,
 concat(environment, '-', s.name) as solver_name,
 concat('0x', encode(reward_target, 'hex')) as reward_target,
 concat('0x', encode(vv.pool, 'hex')) as bonding_pool,
 bp.name as pool_name
from valid_vouches vv
join gnosis_protocol_v2."view_solvers" s
    on address = solver
join bonding_pools bp
    on vv.pool = bp.pool
