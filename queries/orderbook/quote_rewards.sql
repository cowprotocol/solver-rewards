with winning_quotes as (SELECT concat('0x', encode(oq.solver, 'hex')) as solver,
                               oq.order_uid
                        FROM trades t
                               INNER JOIN orders o ON order_uid = uid
                               JOIN order_quotes oq ON t.order_uid = oq.order_uid
                        WHERE (o.class = 'market'
                            OR (o.kind = 'sell' AND (oq.sell_amount - oq.gas_amount * oq.gas_price / oq.sell_token_price) * oq.buy_amount >= o.buy_amount *  oq.sell_amount)
                            OR (o.kind='buy' AND o.sell_amount >= oq.sell_amount + oq.gas_amount * oq.gas_price / oq.sell_token_price))
                          AND o.partially_fillable='f' -- the code above might fail for partially fillable orders
                          AND block_number >= {{start_block}} AND block_number <= {{end_block}}
                          AND oq.solver != '\x0000000000000000000000000000000000000000')

SELECT solver, count(*) AS num_quotes
FROM winning_quotes
GROUP BY solver
