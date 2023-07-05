-- V3: https://dune.com/queries/1320174
select
    solver_address            as receiver,
    sum(gas_price * gas_used) as amount,
    count(*)                  as num_transactions
from cow_protocol_ethereum.batches
    join cow_protocol_ethereum.solvers
        on solver_address = address
where block_time between cast('{{StartTime}}' as timestamp) and cast('{{EndTime}}' as timestamp)
  and environment not in ('services', 'test')
group by solver_address
order by receiver