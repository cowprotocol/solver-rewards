-- Query Here: https://dune.com/queries/1870864
-- The following query shows a complete list of all different selectors
-- used on cow protocol and so far there are no collisions.
-- We can monitor this for new risk free events:
-- https://dune.com/queries/1434731
with interactions as (select selector,
                             target,
                             case
                                 when selector in (
                                                   '\x095ea7b3', -- approve
                                                   '\x2e1a7d4d', -- withdraw
                                                   '\xa9059cbb', -- transfer
                                                   '\x23b872dd' -- transferFrom
                                     ) then true
                                 else false
                                 end as risk_free
                      from gnosis_protocol_v2."GPv2Settlement_evt_Interaction"
                      where evt_block_time between '{{StartTime}}' and '{{EndTime}}'),

     no_interactions as (select tx_hash
                         from gnosis_protocol_v2."batches"
                         where block_time between '{{StartTime}}' and '{{EndTime}}'
                           and tx_hash not in (select evt_tx_hash
                                                   from gnosis_protocol_v2."GPv2Settlement_evt_Interaction"
                                                   where evt_block_time between '{{StartTime}}' and '{{EndTime}}')),

     batch_interaction_counts as (select tx_hash,
                                         count(*)                                          as num_interactions,
                                         sum(case when risk_free = true then 1 else 0 end) as num_risk_fee
                                  from gnosis_protocol_v2."batches" s
                                           inner join gnosis_protocol_v2."GPv2Settlement_evt_Interaction" i
                                                      on tx_hash = i.evt_tx_hash
                                           inner join interactions i2
                                                      on i.selector = i2.selector
                                                          and i.target = i2.target
                                  where block_time between '{{StartTime}}' and '{{EndTime}}'
                                  group by tx_hash),

     combined_risk_free_batches as (select *
                          from batch_interaction_counts
                          where num_interactions = num_risk_fee
                          union
                          select *, 0 as num_interactions, 0 as risk_free
                          from no_interactions)

select concat('0x', encode(tx_hash, 'hex')) as tx_hash
from combined_risk_free_batches