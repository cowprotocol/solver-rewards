WITH observed_settlements AS (SELECT
                                -- settlement
                                tx_hash,
                                solver,
                                s.block_number,
                                -- settlement_observations
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
                              WHERE s.block_number > {{start_block}} AND s.block_number <= {{end_block}}),

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
                                 ON ss.auction_id = ap.auction_id
                       -- outer joins made in order to capture non-existent settlements.
                            LEFT OUTER JOIN observed_settlements os
                                            ON os.auction_id = ss.auction_id),

     reward_per_tx as (SELECT tx_hash,
                              solver,
                              execution_cost,
                              surplus,
                              fee,
                              surplus + fee - reference_score                                                              as uncapped_reward_eth,
                              -- Uncapped Reward = CLAMP_[-E, E + exec_cost](uncapped_reward_eth)
                              LEAST(GREATEST(-{{EPSILON}}, surplus + fee - reference_score), {{EPSILON}} + execution_cost) as capped_reward,
                              winning_score,
                              reference_score,
                              participants                                                                                 as participating_solvers
                       FROM reward_data),

     participation_data as (SELECT tx_hash,
                                   unnest(participating_solvers) as participant
                            FROM reward_per_tx),
     participation_counts as (SELECT participant as solver,
                                     count(*)    as num_participating_batches
                              FROM participation_data
                              GROUP BY participant),
     primary_rewards as (SELECT rpt.solver,
                                SUM(capped_reward)  as total_reward_eth,
                                SUM(execution_cost) as total_exececution_cost_eth
                         FROM reward_per_tx rpt
                         GROUP BY solver)

SELECT concat('0x', encode(pc.solver, 'hex'))                as solver,
       coalesce(total_reward_eth, 0) / pow(10, 18)           as total_reward_eth,
       coalesce(total_exececution_cost_eth, 0) / pow(10, 18) as total_exececution_cost_eth,
       num_participating_batches
FROM participation_counts pc
       LEFT OUTER JOIN primary_rewards pr
                       ON pr.solver = pc.solver;



