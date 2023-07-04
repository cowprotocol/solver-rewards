with winning_quotes as (SELECT concat('0x', encode(oq.solver, 'hex')) as solver,
                               oq.order_uid
                        FROM trades t
                               JOIN order_quotes oq on t.order_uid = oq.order_uid
                        where block_number between {{start_block}} and {{end_block}})

select solver, count(*) as num_quotes
from winning_quotes
group by solver