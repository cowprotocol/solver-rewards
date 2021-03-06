with
-- For a configurable permanent version visit: https://dune.xyz/queries/469110
relevant_batch_info as (
    select concat('0x', encode(solver_address, 'hex')) as solver,
           sum(gas_price_gwei * gas_used) * 10 ^ 9     as eth_spent,
           count(*) * '{{PerBatchReward}}'             as batch_reward,
           sum(num_trades) * '{{PerTradeReward}}'      as trade_reward
    from gnosis_protocol_v2.batches
    where block_time >= '{{StartTime}}'
      and block_time < '{{EndTime}}'
    group by solver
)

select *
from (
         select 'native'  as token_type,
                null      as token_address,
                solver    as receiver,
                eth_spent::numeric::text as amount
         from relevant_batch_info
         union
         select 'erc20'                                      as token_type,
                '0xDEf1CA1fb7FBcDC777520aa7f396b4E015F497aB' as token_address,
                solver                                       as receiver,
                (10^18 * (batch_reward + trade_reward))::numeric::text    as amount
         from relevant_batch_info
     ) as _
order by receiver, token_address desc
