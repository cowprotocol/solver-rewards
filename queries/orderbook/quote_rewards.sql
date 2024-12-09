with winning_quotes as (
    select
        concat('0x', encode(oq.solver, 'hex')) as solver,
        oq.order_uid
    from
        trades t
        inner join orders o on order_uid = uid
        join order_quotes oq on t.order_uid = oq.order_uid
    where
        (
            o.class = 'market'
            or (
                o.kind = 'sell'
                and (
                    oq.sell_amount - oq.gas_amount * oq.gas_price / oq.sell_token_price
                ) * oq.buy_amount >= o.buy_amount * oq.sell_amount
            )
            or (
                o.kind = 'buy'
                and o.sell_amount >= oq.sell_amount + oq.gas_amount * oq.gas_price / oq.sell_token_price
            )
        )
        and o.partially_fillable = 'f' -- the code above might fail for partially fillable orders
        and block_number >= {{start_block}}
        and block_number <= {{end_block}}
        and oq.solver != '\x0000000000000000000000000000000000000000'
)
select
    solver,
    count(*) as num_quotes
from
    winning_quotes
group by
    solver