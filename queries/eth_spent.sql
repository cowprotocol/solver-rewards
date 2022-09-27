-- V1: https://dune.com/queries/1320169
select concat('0x', encode(solver_address, 'hex')) as receiver,
       sum(gas_price_gwei * gas_used) * 10 ^ 9     as amount
from gnosis_protocol_v2.batches
join gnosis_protocol_v2.view_solvers
    on solver_address = address
where block_time between '{{StartTime}}' and '{{EndTime}}'
  and environment not in ('services', 'test')
group by receiver
order by amount desc

-- --! They do not seem to agree!
-- -- V2: https://dune.com/queries/1320174
-- select solver_address as receiver,
--        cast(sum(gas_price * gas_used) as decimal(38,0))::string     as eth_spent
-- from cow_protocol_ethereum.batches
-- join cow_protocol_ethereum.solvers
--     on solver_address = address
-- where block_time between '{{StartTime}}' and '{{EndTime}}'
--   and environment not in ('services', 'test')
-- group by receiver