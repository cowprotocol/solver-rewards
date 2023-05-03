-- V3 Query: https://dune.com/queries/1785586
select
    solver_address as solver,
    sum(num_trades) as num_trades
from cow_protocol_ethereum.batches
where block_number between {{start_block}} and {{end_block}}
group by solver_address
order by num_trades desc, solver
