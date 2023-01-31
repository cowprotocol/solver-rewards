-- V2: https://dune.com/queries/1320174
select
    solver_address                                                                         as receiver,
    cast(sum((gas_price * gas_used) / pow(10, 18)) * pow(10,18) as decimal(38, 0))::string as amount,
    count(*) as num_transactions
from cow_protocol_ethereum.batches
    join cow_protocol_ethereum.solvers
        on solver_address = address
where block_time between '{{StartTime}}' and '{{EndTime}}'
  and environment not in ('services', 'test')
group by receiver
order by receiver
