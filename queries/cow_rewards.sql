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
                      where block_number between 15719995 and 15727058)

select concat('0x', encode(solver, 'hex'))          as receiver,
       -- This column will be used to compare with Dune:
       -- cross referencing that all trades are accounted for in the orderbook
       count(*) as num_trades,
       (sum(reward) * pow(10, 18))::numeric::text   as amount,
       '0xDEf1CA1fb7FBcDC777520aa7f396b4E015F497aB' as token_address
from trade_hashes
         -- Inner join because both prod and staging DB index trades and settlements,
-- but the rewards for each environment are contained only in respective databases.
         inner join order_rewards
                    on trade_hashes.order_uid = order_rewards.order_uid
group by solver;
