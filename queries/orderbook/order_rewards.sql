with trade_hashes as (SELECT solver,
                             order_uid,
                             fee_amount,
                             settlement.tx_hash,
                             auction_id
                      FROM trades t
                               LEFT OUTER JOIN LATERAL (
                          SELECT tx_hash, solver, tx_nonce, tx_from
                          FROM settlements s
                          WHERE s.block_number = t.block_number
                            AND s.log_index > t.log_index
                          ORDER BY s.log_index ASC
                          LIMIT 1
                          ) AS settlement ON true
                               join auction_transaction
                          -- This join also eliminates overlapping
                          -- trades & settlements between barn and prod DB
                                   on settlement.tx_from = auction_transaction.tx_from
                                       and settlement.tx_nonce = auction_transaction.tx_nonce
                      where block_number between {{start_block}} and {{end_block}})

-- Most efficient column order for sorting would be having tx_hash or order_uid first
select concat('0x', encode(trade_hashes.order_uid, 'hex')) as order_uid,
       concat('0x', encode(solver, 'hex'))  as solver,
       concat('0x', encode(tx_hash, 'hex')) as tx_hash,
       coalesce(surplus_fee, 0)             as surplus_fee,
       coalesce(reward, 0.0)                as amount
from trade_hashes
         left outer join {{reward_table}} o
                         on trade_hashes.order_uid = o.order_uid
                             and trade_hashes.auction_id = o.auction_id;
