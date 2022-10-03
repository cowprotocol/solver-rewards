with trade_hashes as (SELECT solver,
                             order_uid,
                             settlement.tx_hash
                      FROM trades t
                               LEFT OUTER JOIN LATERAL (
                          SELECT tx_hash, solver
                          FROM settlements s
                          WHERE s.block_number = t.block_number
                            AND s.log_index > t.log_index
                          ORDER BY s.log_index ASC
                          LIMIT 1
                          ) AS settlement ON true
                      where block_number between {{start_block}} and {{end_block}}),
     -- Usually this would be sufficient. However some orders are not actually in the DB.
     db_order_counts as (select solver, count(order_uid) as num_orders, tx_hash
                         from trade_hashes
                                  inner join orders
                                             on order_uid = uid
                         group by solver, tx_hash),
     corrected_trade_counts as (select solver,
                                       tx_hash,
                                       num_orders,
                                       num_trades,
                                       num_trades - num_orders as missing_orders
                                from db_order_counts tc
                                         inner join lateral (
                                    select count(order_uid) as num_trades,
                                           tx_hash          as hash
                                    from trade_hashes
                                    group by tx_hash
                                    ) as th on tc.tx_hash = th.hash),

     final_counts as (select concat('0x', encode(solver, 'hex')) as receiver,
                             count(tx_hash)                      as num_batches,
                             sum(num_trades)                     as num_trades,
                             sum(missing_orders)                 as missing_orders
                      from corrected_trade_counts
                      group by solver)

select *,
       ((50 * num_batches + 35 * num_trades) * pow(10, 18))::numeric::text as amount,
       '0xDEf1CA1fb7FBcDC777520aa7f396b4E015F497aB'                        as token_address
from final_counts
order by receiver;

-- There is currently a bug in orderbook (missing entries in solver_competitions table)
-- with solver_solutions as (select concat('0x', encode(solver, 'hex'))    as receiver,
--
--                                  count(*)                               as num_batches,
--                                  -- winning solution is the last element of the array solutions array.
--                                  -- 1. extract solutions from json,
--                                  -- 2. pop the last element of the array
--                                  -- 3. and extract the length of the orders in it
--                                  sum(jsonb_array_length(json -> 'solutions' ->
--                                                         jsonb_array_length(json -> 'solutions') -
--                                                         1 -> 'orders')) as num_trades
--                           from solver_competitions sc
--                                    inner join settlements s
--                                               on s.tx_hash = sc.tx_hash
--                           where s.block_number between {{start_block}} and {{end_block}}
--                           group by solver)
--
-- select '0xDEf1CA1fb7FBcDC777520aa7f396b4E015F497aB'                        as token_address,
--        receiver,
--        ((50 * num_batches + 35 * num_trades) * pow(10, 18))::numeric::text as amount
-- from solver_solutions
-- order by receiver;