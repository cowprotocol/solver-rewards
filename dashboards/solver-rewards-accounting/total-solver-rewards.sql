with 
-- For a permanent version of this Query visit: https://dune.xyz/queries/448457/852218
solver_rewards as (
    select
        concat(
            to_char('{{StartTime}}'::timestamptz, 'YYYY-MM-DD'),
            ' to ',
            to_char('{{StartTime}}'::timestamptz + interval '6 day', 'YYYY-MM-DD')
        ) as accounting_period,
        sum(gas_price_gwei * gas_used) / 10 ^ 9 as execution_cost_eth,
        count(*) * 100 as cow_rewards
    from gnosis_protocol_v2.batches
    where block_time >= '{{StartTime}}'
    and block_time < '{{StartTime}}'::timestamptz + interval '7 day'
),

realized_fees as (
    select
        concat(
            to_char('{{StartTime}}'::timestamptz, 'YYYY-MM-DD'),
            ' to ',
            to_char('{{StartTime}}'::timestamptz + interval '6 day', 'YYYY-MM-DD')
        ) as accounting_period,
        sum(atoms_bought) / 10^18 as realized_fees_eth
    from gnosis_protocol_v2."trades"
    where trader in (
        select address
        from gnosis_protocol_v2."view_solvers"
        where name = 'Withdraw'
    )
    and block_time >= '{{StartTime}}'
    and block_time < '{{StartTime}}'::timestamptz + interval '7 day'
)

select 
    r.accounting_period,
    execution_cost_eth,
    cow_rewards,
    realized_fees_eth
from solver_rewards r
join realized_fees f
    on r.accounting_period = f.accounting_period
