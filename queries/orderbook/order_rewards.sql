with trade_hashes as (SELECT solver,
                             order_uid,
                             fee_amount,
                             settlement.tx_hash,
                             solver_competitions.id as auction_id
                      FROM trades t
                               LEFT OUTER JOIN LATERAL (
                          SELECT tx_hash, solver
                          FROM settlements s
                          WHERE s.block_number = t.block_number
                            AND s.log_index > t.log_index
                          ORDER BY s.log_index ASC
                          LIMIT 1
                          ) AS settlement ON true
                               join solver_competitions
                          -- This join also eliminates overlapping
                          -- trades & settlements between barn and prod DB
                                    on settlement.tx_hash = solver_competitions.tx_hash
                      where block_number between {{start_block}} and {{end_block}})

-- Most efficient column order for sorting would be having tx_hash or order_uid first
select concat('0x', encode(trade_hashes.order_uid, 'hex')) as order_uid,
       concat('0x', encode(solver, 'hex'))  as solver,
       concat('0x', encode(tx_hash, 'hex')) as tx_hash,
       coalesce(reward, 0.0)                as amount,
       -- An order is a liquidity order if and only if reward is null.
       -- A liquidity order is safe if and only if its fee_amount is > 0
       case
           when reward is null and fee_amount > 0 then True
           when reward is null and fee_amount = 0 then False
           end                              as safe_liquidity
from trade_hashes
         left outer join order_rewards
                         on trade_hashes.order_uid = order_rewards.order_uid
                             and trade_hashes.auction_id = order_rewards.auction_id;
