with winning_quotes as (SELECT concat('0x', encode(oq.solver, 'hex')) as solver,
                               oq.order_uid
                        FROM trades t
                               INNER JOIN orders o ON order_uid = uid
                               JOIN order_quotes oq ON t.order_uid = oq.order_uid
                        WHERE o.class = 'market'
                          AND block_number BETWEEN {{start_block}} AND {{end_block}}
                          AND oq.solver != '\x0000000000000000000000000000000000000000')

SELECT solver, count(*) AS num_quotes
FROM winning_quotes
GROUP BY solver