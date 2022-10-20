with trade_hashes as (SELECT solver,
                             order_uid,
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

select concat('0x', encode(solver, 'hex'))          as receiver,
       -- Used to compare with Dune (cross referencing that all trades are accounted for in the orderbook)
       count(*) as num_trades,
       (sum(coalesce(reward, 0)) * pow(10, 18))::numeric::text   as amount,
       '0xDEf1CA1fb7FBcDC777520aa7f396b4E015F497aB' as token_address
from trade_hashes
        -- outer join because there are missing records in order rewards:
        -- e.g. order_uid 0x9CB39E52C3ABD20F38830E70E31E38DEBC12349CA680E7F1DAA4B47B704394D65FCDC32DFC361A32E9D5AB9A384B890C62D0B8AC634D8F38
         left outer join order_rewards
                    on trade_hashes.order_uid = order_rewards.order_uid
                    and trade_hashes.auction_id = order_rewards.auction_id
group by solver;
