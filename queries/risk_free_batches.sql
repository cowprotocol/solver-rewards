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

     no_interactions as (select evt_tx_hash
                         from gnosis_protocol_v2."GPv2Settlement_evt_Settlement"
                         where evt_block_time between '{{StartTime}}' and '{{EndTime}}'
                           and evt_tx_hash not in (select evt_tx_hash
                                                   from gnosis_protocol_v2."GPv2Settlement_evt_Interaction"
                                                   where evt_block_time between '{{StartTime}}' and '{{EndTime}}')),

     batch_interaction_counts as (select s.evt_tx_hash,
                                         count(*)                                          as num_interactions,
                                         sum(case when risk_free = true then 1 else 0 end) as risk_free
                                  from gnosis_protocol_v2."GPv2Settlement_evt_Settlement" s
                                           inner join gnosis_protocol_v2."GPv2Settlement_evt_Interaction" i
                                                      on s.evt_tx_hash = i.evt_tx_hash
                                           inner join interactions i2
                                                      on i.selector = i2.selector
                                                          and i.target = i2.target
                                  where s.evt_block_time between '{{StartTime}}' and '{{EndTime}}'
                                  group by s.evt_tx_hash),

     combined_results as (select *
                          from batch_interaction_counts
                          where num_interactions = risk_free
                          union
                          select *, 0 as num_interactions, 0 as risk_free
                          from no_interactions)

select concat('0x', encode(evt_tx_hash, 'hex')) as tx_hash
from combined_results