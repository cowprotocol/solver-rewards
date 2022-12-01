with
-- V1 Query: https://dune.com/queries/1687752
execution_costs as (
    SELECT
        success,
        sum((gas_used * gas_price)/ pow(10, 18)) as gas_cost_eth
    FROM ethereum.transactions as tx
    where block_time between '{{StartTime}}' and '{{EndTime}}'
    AND position('0x13d79a0b' in data) > 0 --! settle method ID
    AND to = lower('0x9008D19f58AAbD9eD0D60971565AA8510560ab41')
    group by success
),
solver_rewards as (
    select
        sum(value) / pow(10, 18) as cow_rewards
    from cow_protocol_ethereum.CowProtocolToken_evt_Transfer
    where from = lower('0xA03be496e67Ec29bC62F01a428683D7F9c204930')
    and evt_block_time between '{{StartTime}}' and '{{EndTime}}'
),
batch_details as (
    select
        count(*) as batches_settled,
        sum(num_trades) as num_trades
    from cow_protocol_ethereum.batches
    where block_time >= '{{StartTime}}' and block_time < '{{EndTime}}'
),
realized_fees as (
    select
        sum(atoms_bought) / pow(10, 18) as realized_fees_eth
    from cow_protocol_ethereum.trades
    where trader in (
        select address
        from cow_protocol_ethereum.solvers
        where name = 'Withdraw'
    )
    and block_time between '{{StartTime}}' and '{{EndTime}}'
)

select
    concat('{{StartTime}}'::date, ' to ', '{{EndTime}}'::date - interval '1 day') as accounting_period,
    (select gas_cost_eth from execution_costs where success = true) as execution_cost_eth,
    (select gas_cost_eth from execution_costs where success = false) as failure_cost_eth,
    (select realized_fees_eth from realized_fees) as realized_fees_eth,
    (select cow_rewards from solver_rewards) as cow_reward,
    (select batches_settled from batch_details) as batches_settled,
    (select num_trades from batch_details) as num_trades
