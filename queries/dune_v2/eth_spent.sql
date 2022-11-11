-- V2: https://dune.com/queries/1320174
select
    solver as receiver,
    cast(sum(gas_price * gas_used) as decimal(38,0))::string     as amount
from gnosis_protocol_v2_ethereum.GPv2Settlement_evt_Settlement
inner join ethereum.transactions
    on lower(evt_tx_hash) = lower(hash)
    and block_time between '{{StartTime}}' and '{{EndTime}}'
join cow_protocol_ethereum.solvers
    on solver = address
where evt_block_time between '{{StartTime}}' and '{{EndTime}}'
    and environment not in ('service', 'test')
group by solver
order by amount desc;

-- -- Alternate (faster version of the query using batches table).
-- -- https://dune.com/queries/1564519
-- -- The tradeoff is faster execution with slight latency issue
-- -- (batches only refreshed once per hour)
-- -- More context: https://github.com/cowprotocol/solver-rewards/pull/133#discussion_r1018897572
-- select solver_address                                            as receiver,
--        cast(sum(gas_price * gas_used) as decimal(38, 0))::string as eth_spent
-- from cow_protocol_ethereum.batches
--          join cow_protocol_ethereum.solvers
--               on solver_address = address
-- where block_time between '{{StartTime}}' and '{{EndTime}}'
--   and environment not in ('services', 'test')
-- group by receiver