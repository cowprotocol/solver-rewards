-- V1: https://dune.com/queries/1320169
select concat('0x', encode(solver_address, 'hex')) as receiver,
       sum(gas_price_gwei * gas_used) * 10 ^ 9     as amount,
       count(*) as num_transactions
from gnosis_protocol_v2.batches
join gnosis_protocol_v2.view_solvers
    on solver_address = address
where block_time between '{{StartTime}}' and '{{EndTime}}'
  and environment not in ('services', 'test')
group by receiver
order by amount desc
