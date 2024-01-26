WITH observed_settlements AS (SELECT
                                -- settlement
                                tx_hash,
                                solver,
                                s.block_number,
                                -- settlement_observations
                                effective_gas_price * gas_used AS execution_cost,
                                surplus,
                                fee,
                                s.auction_id
                              FROM settlement_observations so
                                     JOIN settlements s
                                          ON s.block_number = so.block_number
                                            AND s.log_index = so.log_index
                                     JOIN settlement_scores ss
                                          ON s.auction_id = ss.auction_id
                              WHERE ss.block_deadline >= {{start_block}}
                                AND ss.block_deadline <= {{end_block}}),

     auction_participation as (SELECT ss.auction_id, array_agg(participant) as participating_solvers
                               FROM auction_participants
                                      JOIN settlement_scores ss
                                           ON auction_participants.auction_id = ss.auction_id
                               WHERE block_deadline >= {{start_block}}
                                 AND block_deadline <= {{end_block}}
                               GROUP BY ss.auction_id),
     reward_data AS (SELECT
                       -- observations
                       tx_hash,
                       ss.auction_id,
                       -- TODO - Assuming that `solver == winner` when both not null
                       --  We will need to monitor that `solver == winner`!
                       coalesce(solver, winner)               as solver,
                       block_number                           as settlement_block,
                       block_deadline,
                       case
                         when block_number is not null and block_number > block_deadline then 0
                         else coalesce(execution_cost, 0) end as execution_cost,
                       case
                         when block_number is not null and block_number > block_deadline then 0
                         else coalesce(surplus, 0) end        as surplus,
                       case
                         when block_number is not null and block_number > block_deadline then 0
                         else coalesce(fee, 0) end            as fee,
                       -- scores
                       winning_score,
                       reference_score,
                       -- auction_participation
                       participating_solvers
                     FROM settlement_scores ss
                            -- If there are reported scores,
                            -- there will always be a record of auction participants
                            JOIN auction_participation ap
                                 ON ss.auction_id = ap.auction_id
                       -- outer joins made in order to capture non-existent settlements.
                            LEFT OUTER JOIN observed_settlements os
                                            ON os.auction_id = ss.auction_id),
     reward_per_auction as (SELECT tx_hash,
                                   auction_id,
                                   settlement_block,
                                   block_deadline,
                                   solver,
                                   execution_cost,
                                   surplus,
                                   fee,
                                   surplus + fee - reference_score as uncapped_reward_eth,
                                   -- Uncapped Reward = CLAMP_[-E, E + exec_cost](uncapped_reward_eth)
                                   LEAST(GREATEST(-{{EPSILON}}, surplus + fee - reference_score),
                                     {{EPSILON}} + execution_cost) as capped_payment,
                                   winning_score,
                                   reference_score,
                                   participating_solvers           as participating_solvers
                            FROM reward_data),
     participation_data as (SELECT tx_hash, unnest(participating_solvers) as participant
                            FROM reward_per_auction),
     participation_counts as (SELECT participant as solver, count(*) as num_participating_batches
                              FROM participation_data
                              GROUP BY participant),
     primary_rewards as (SELECT rpt.solver,
                                SUM(capped_payment) as payment_wei,
                                SUM(execution_cost) as exececution_cost_wei
                         FROM reward_per_auction rpt
                         GROUP BY solver),
     aggregate_results as (SELECT concat('0x', encode(pc.solver, 'hex')) as solver,
                                  coalesce(payment_wei, 0)               as payment_eth,
                                  coalesce(exececution_cost_wei, 0)      as execution_cost_eth,
                                  num_participating_batches
                           FROM participation_counts pc
                                  LEFT OUTER JOIN primary_rewards pr
                                                  ON pr.solver = pc.solver)

select *
from aggregate_results
order by solver;
