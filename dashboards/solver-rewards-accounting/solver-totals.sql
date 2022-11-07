with
-- EVM Solver Data for Period:
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
    where block_time between '{{StartTime}}' and '{{EndTime}}'
    group by solver,solver_name, environment, name
    order by execution_cost_eth desc
),

pre_solver_results as (
    select
        concat('0x', encode(solver, 'hex')) as solver,
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

evm_solver_results as (
    select
        pre.*,
        coalesce(num_liquidity_orders, 0) as evm_liquidity_orders
    from pre_solver_results pre
    left outer join liquidity_orders lo
        on pre.solver = lo.solver
),

-- Orderbook Solver Data for Period
risky_batches as (
    select
        distinct evt_tx_hash,
        false as risk_free
    from gnosis_protocol_v2."GPv2Settlement_evt_Interaction"
    where evt_block_time between '{{StartTime}}' and '{{EndTime}}'
    and selector not in (
                '\x095ea7b3', -- approve
                '\x2e1a7d4d', -- withdraw
                '\xa9059cbb', -- transfer
                '\x23b872dd'  -- transferFrom
            )
),

per_order_rewards as (
    select
      s.solver,
      tx_hash,
      amount,
      safe_liquidity
    from gnosis_protocol_v2."GPv2Settlement_evt_Settlement" s
    inner join dune_user_generated.cow_order_rewards_barn
        on tx_hash = evt_tx_hash
        and evt_block_time between '{{StartTime}}' and '{{EndTime}}'
),

batchwise_order_counts as (
    select
        solver,
        tx_hash,
        count(*) as num_trades,
        sum(case when amount > 0 then 1 else 0 end) as user_orders,
        sum(case when amount = 0 then 1 else 0 end) as liquidity_orders,
        sum(case when safe_liquidity is false then 1 else 0 end) as unsafe_liquidity_orders,
        coalesce(risk_free, true) as risk_free
    from per_order_rewards outer_rewards
    left outer join risky_batches
        on tx_hash = evt_tx_hash
    group by tx_hash, solver, risk_free
),

orderbook_solver_results as (
    select
        concat('0x', encode(boc.solver, 'hex')) as solver,
        sum(num_trades) as orderbook_trades,
        sum(user_orders) as user_orders,
        sum(liquidity_orders) as orderbook_liquidity_orders,
        sum(unsafe_liquidity_orders) as unsafe_liquidity,
        sum((
            select sum(
                case when amount > 0 and risk_free = True and unsafe_liquidity_orders = 0
                    then 37.0
                    else amount
                end)
            from per_order_rewards
            where boc.tx_hash = tx_hash
        )) as cow_reward
    from batchwise_order_counts boc
    group by boc.solver
),

solver_totals as (
    select
        esr.solver,
        concat(environment, '-', name) as solver_name,
        execution_cost_eth,
        batches_settled,
        -- These should be equal num_trades
        num_trades, -- orderbook_trades,
        user_orders,
        evm_liquidity_orders as liquidity_orders, -- orderbook_liquidity
        unsafe_liquidity,
        cow_reward,
        -- This links to Solver Per Batch Rewards: https://dune.com/queries/1468233
        -- Which further links to Order Rewards for Batch: https://dune.com/queries/1530613
        concat('<a href="https://dune.com/queries/1468233?SolverAddress=', osr.solver, '&StartTime={{StartTime}}&EndTime={{EndTime}}" target="_blank">link</a>') as details
    from evm_solver_results esr
    left join orderbook_solver_results osr
        on esr.solver = osr.solver
)

select * from solver_totals


