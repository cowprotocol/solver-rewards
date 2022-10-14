-- V1: https://dune.com/queries/1403457
select concat('0x', encode(address, 'hex')) as solver,
       sum(gas_price * gas_used) as eth_spent,
       count(*) as num_transactions
from gnosis_protocol_v2.view_solvers
inner join ethereum.transactions
    on "from" = address
    and "to" = '\x9008d19f58aabd9ed0d60971565aa8510560ab41'
    and position('\x13d79a0b' in data) > 0 --! settle method ID
    and block_time between '{{StartTime}}' and '{{EndTime}}'
    and success = true
    and environment not in ('services', 'test')
group by solver
order by eth_spent desc

-- -- V2: https://dune.com/queries/1403493
-- select address as solver,
--        sum(gas_price * gas_used) / pow(10, 18) as eth_spent,
--        count(*) as num_transactions
-- from cow_protocol_ethereum.solvers
-- inner join ethereum.transactions
--     on from = address
--     and block_time between '{{StartTime}}' and '{{EndTime}}'
--     and to = '0x9008d19f58aabd9ed0d60971565aa8510560ab41'
--     and position('0x13d79a0b' in data) > 0 --! settle method ID
--     and success = true
--     and environment not in ('services', 'test')
-- group by solver
-- order by eth_spent desc