with
relevant_batch_info as (
    select concat('0x', encode(solver_address, 'hex')) as solver,
           count(*) * '{{PerBatchReward}}'             as batch_reward,
           sum(num_trades) * '{{PerTradeReward}}'      as trade_reward
    from gnosis_protocol_v2.batches
    join gnosis_protocol_v2.view_solvers
        on solver_address = address
    where block_time >= '{{StartTime}}'
      and block_time < '{{EndTime}}'
      and environment not in ('services', 'test')
    group by solver
)
select
    '0xDEf1CA1fb7FBcDC777520aa7f396b4E015F497aB' as token_address,
    solver                                       as receiver,
    (10^18 * (batch_reward + trade_reward))::numeric::text    as amount
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