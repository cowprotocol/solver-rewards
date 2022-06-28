with
solver_data as (
    select
        solver_address as solver,
        environment,
        name,
        solver_name,
        sum(gas_price_gwei * gas_used) / 10 ^ 9 as execution_cost_eth,
        count(*) as batches_settled,
        sum(num_trades) as num_trades
    from gnosis_protocol_v2."batches"
    join gnosis_protocol_v2."view_solvers"
        on solver_address = address
    where block_time >= '{{StartTime}}'
    and block_time < '{{EndTime}}'
    group by solver,solver_name, environment, name
    order by execution_cost_eth desc
),

per_solver_results as (
    select
        concat('0x', encode(solver, 'hex')) as solver_address,
        environment,
        name,
        execution_cost_eth,
        batches_settled,
        num_trades
    from solver_data sd
)

-- -- END SOLVER REWARDS
select
    solver_address, 
    concat(environment, '-', name) as solver_name, 
    execution_cost_eth, 
    batches_settled,
    num_trades,
    batches_settled * '{{PerBatchReward}}' + num_trades * '{{PerTradeReward}}' as cow_reward
from per_solver_results
