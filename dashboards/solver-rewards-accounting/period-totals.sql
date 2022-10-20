with
solver_rewards as (
    select
        concat(
            to_char('{{StartTime}}'::timestamptz, 'YYYY-MM-DD'),
            ' to ',
            to_char('{{EndTime}}'::timestamptz - interval '1 day', 'YYYY-MM-DD')
        ) as accounting_period,
        sum(gas_price_gwei * gas_used) / 10 ^ 9 as execution_cost_eth,
        count(*) as batches_settled,
        sum(num_trades) as num_trades
    from gnosis_protocol_v2.batches
    where block_time between '{{StartTime}}' and '{{EndTime}}'
),

realized_fees as (
    select
        concat(
            to_char('{{StartTime}}'::timestamptz, 'YYYY-MM-DD'),
            ' to ',
            to_char('{{EndTime}}'::timestamptz - interval '1 day', 'YYYY-MM-DD')
        ) as accounting_period,
        sum("buyAmount") / 10^18 as realized_fees_eth
    from gnosis_protocol_v2."GPv2Settlement_evt_Trade"
    where owner in (
        select address
        from gnosis_protocol_v2."view_solvers"
        where name = 'Withdraw'
    )
    and evt_block_time between '{{StartTime}}' and '{{EndTime}}'
)

select
    r.accounting_period,
    execution_cost_eth,
    realized_fees_eth,
    realized_fees_eth / execution_cost_eth as cost_coverage,
    (select sum(cow_reward) from dune_user_generated.cow_rewards_{{PeriodHash}}) as cow_rewards,
    batches_settled,
    num_trades,
    num_trades / batches_settled as average_batch_size
from solver_rewards r
join realized_fees f
    on r.accounting_period = f.accounting_period
