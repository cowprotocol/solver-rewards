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
),

liquidity_orders as (
    select
        concat('0x', encode(solver_address, 'hex')) as solver,
        count(*) as num_liquidity_orders
    from gnosis_protocol_v2."trades" t
    join gnosis_protocol_v2."batches" b
        on t.tx_hash = b.tx_hash
    where fee = 0
    and b.block_time between '{{StartTime}}' and '{{EndTime}}'
    group by solver_address
),

-- Must ensure this table exists before execution!
orderbook_data as (
    select solver, num_trades as orderbook_trades, cow_reward
    from dune_user_generated.cow_rewards_{{PeriodHash}}
)

-- -- END SOLVER REWARDS
select
    solver_address,
    concat(environment, '-', name) as solver_name,
    execution_cost_eth,
    batches_settled,
    num_trades,
    coalesce(num_liquidity_orders, 0) as liquidity_orders,
    orderbook_trades,
    1.0 * cow_reward / pow(10, 18) as cow_reward
from per_solver_results
left outer join liquidity_orders lo
    on solver_address = lo.solver
left outer join orderbook_data od -- Just in case its not there.
    on solver_address = od.solver

