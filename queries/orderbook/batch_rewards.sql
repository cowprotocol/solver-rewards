WITH observed_settlements AS (SELECT
                                -- settlement
                                tx_hash,
                                solver,
                                -- settlement_observations
                                block_number,
                                effective_gas_price * gas_used AS execution_cost,
                                surplus,
                                fee,
                                -- auction_transaction
                                auction_id
                              FROM settlement_observations so
                                     JOIN settlements s
                                          ON s.block_number = so.block_number
                                            AND s.log_index = so.log_index
                                     JOIN auction_transaction at
                                          ON s.tx_from = at.tx_from
                                            AND s.tx_nonce = at.tx_nonce
                              WHERE block_number > {{start_block}} AND block_number <= {{end_block}}),

     reward_data AS (SELECT
                       -- observations
                       tx_hash,
                       coalesce(
                               solver,
                         -- This is the winning solver (i.e. last entry of participants array)
                               participants[array_length(participants, 1)]
                         )                                    as solver,
                       -- Right-hand terms in coalesces below represent the case when settlement
                       -- observations are unavailable (i.e. no settlement corresponds to reported scores).
                       -- In particular, this means that surplus, fee and execution cost are all zero.
                       -- When there is an absence of settlement block number, we fall back
                       -- on the block_deadline from the settlement_scores table.
                       coalesce(block_number, block_deadline) as block_number,
                       coalesce(execution_cost, 0)            as execution_cost,
                       coalesce(surplus, 0)                   as surplus,
                       coalesce(fee, 0)                       as fee,
                       surplus + fee - reference_score        AS payment,
                       -- scores
                       winning_score,
                       reference_score,
                       -- participation
                       participants
                     FROM settlement_scores ss
                            -- If there are reported scores,
                            -- there will always be a record of auction participants
                            JOIN auction_participants ap
                                 ON os.auction_id = ap.auction_id
                       -- outer joins made in order to capture non-existent settlements.
                            LEFT OUTER JOIN observed_settlements os
                                            ON os.auction_id = ss.auction_id),

     reward_per_tx as (SELECT tx_hash,
                              solver,
                              execution_cost,
                              surplus,
                              fee,
                              surplus + fee - reference_score as reward_eth,
                              winning_score,
                              reference_score,
                              participants                    as participating_solvers
                       FROM reward_data),
     participation_data as (select tx_hash, unnest(participating_solvers) as participant
                            from reward_per_tx),
     participation_counts as (select participant as solver, count(tx_hash) as num_participating_batches
                              from participation_data
                              group by participant),
     primary_rewards as (select rpt.solver, sum(reward_eth) as total_reward_eth
                         from reward_per_tx rpt
                         group by solver)

select concat('0x', encode(pr.solver, 'hex')) as solver,
       total_reward_eth,
       num_participating_batches
from primary_rewards pr
       join participation_counts pc
            on pr.solver = pc.solver



