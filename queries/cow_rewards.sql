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
                      join solver_competitions on settlement.tx_hash = solver_competitions.tx_hash
                      where block_number between {{start_block}} and {{end_block}})

select concat('0x', encode(solver, 'hex'))          as receiver,
       -- Used to compare with Dune (cross referencing that all trades are accounted for in the orderbook)
       count(*) as num_trades,
       (sum(reward) * pow(10, 18))::numeric::text   as amount,
       '0xDEf1CA1fb7FBcDC777520aa7f396b4E015F497aB' as token_address
from trade_hashes
         -- Inner join because both prod and staging DB index trades and settlements,
-- but the rewards for each environment are contained only in respective databases.
         inner join order_rewards
                    on trade_hashes.order_uid = order_rewards.order_uid
                    and trade_hashes.auction_id = order_rewards.auction_id
group by solver;
