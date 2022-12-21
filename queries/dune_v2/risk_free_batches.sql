with
interactions as (
    select
        selector,
        target,
        case
            when selector in (
                '0x095ea7b3', -- approve
                '0x2e1a7d4d', -- withdraw
                '0xa9059cbb', -- transfer
                '0x23b872dd'  -- transferFrom
            ) then true
            else false
        end as risk_free
    from gnosis_protocol_v2_ethereum.GPv2Settlement_evt_Interaction
    where evt_block_time between '{{StartTime}}' and '{{EndTime}}'
),

no_interactions as (
    select tx_hash
    from cow_protocol_ethereum.batches
    where block_time between '{{StartTime}}' and '{{EndTime}}'
    and tx_hash not in (
        select evt_tx_hash
        from gnosis_protocol_v2_ethereum.GPv2Settlement_evt_Interaction
        where evt_block_time between '{{StartTime}}' and '{{EndTime}}'
    )
),

batch_interaction_counts as (
    select
        tx_hash,
        count(*) as num_interactions,
        sum(case when risk_free = true then 1 else 0 end) as risk_free
    from cow_protocol_ethereum.batches b
    inner join gnosis_protocol_v2_ethereum.GPv2Settlement_evt_Interaction i
        on tx_hash = i.evt_tx_hash
    inner join interactions i2
        on i.selector = i2.selector
        and i.target = i2.target
    where b.block_time between '{{StartTime}}' and '{{EndTime}}'
    group by tx_hash
),

combined_results as (
    select * from batch_interaction_counts where num_interactions = risk_free
    union
    select *, 0 as num_interactions, 0 as risk_free from no_interactions
)

select tx_hash from combined_results