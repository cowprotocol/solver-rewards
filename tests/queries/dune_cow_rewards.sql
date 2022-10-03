with
relevant_batch_info as (
    select
        concat('0x', encode(solver_address, 'hex')) as solver,
        sum(case when fee = 0 then 1 else 0 end) as jit_orders,
        count(*) as num_trades,
        count(distinct b.tx_hash) as num_batches
    from gnosis_protocol_v2."trades" t
    join gnosis_protocol_v2."batches" b
        on t.tx_hash = b.tx_hash
    and b.block_time between '{{StartTime}}' and '{{EndTime}}'
    group by solver_address
)

select
    '0xDEf1CA1fb7FBcDC777520aa7f396b4E015F497aB' as token_address,
    solver                                       as receiver,
    (10^18 * ('{{PerBatchReward}}' * num_batches + '{{PerTradeReward}}' * (num_trades - jit_orders)))::numeric::text    as amount
 from relevant_batch_info

-- -- V2: https://dune.com/queries/1320220
-- with
-- relevant_batch_info as (
--     select solver_address,
--            count(*) * '{{PerBatchReward}}'             as batch_reward,
--            sum(num_trades) * '{{PerTradeReward}}'      as trade_reward
--     from cow_protocol_ethereum.batches
--     join cow_protocol_ethereum.solvers
--         on solver_address = address
--     where block_time between '{{StartTime}}' and '{{EndTime}}'
--       and environment not in ('services', 'test')
--     group by solver_address
-- )
-- select
--     '0xDEf1CA1fb7FBcDC777520aa7f396b4E015F497aB'                               as token_address,
--     solver_address                                                             as receiver,
--     cast((batch_reward + trade_reward) * pow(10, 18) as decimal(38,0))::string as amount
--  from relevant_batch_info