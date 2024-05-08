WITH batch_data_raw AS (
    SELECT
        -- scores
        concat('0x', encode(ss.winner, 'hex')) as winning_solver,
        ss.auction_id,
        ss.block_deadline,
        ss.winning_score,
        ss.reference_score,
        -- settlement
        CASE WHEN s.tx_hash IS NULL THEN NULL
            ELSE concat('0x', encode(s.tx_hash, 'hex'))
        END AS tx_hash,
        s.block_number,
        s.log_index,
        -- settlement observations
        so.effective_gas_price,
        so.gas_used,
        so.surplus,
        so.fee
    FROM
        settlement_scores ss
        LEFT OUTER JOIN settlements s
        ON s.auction_id = ss.auction_id
        LEFT OUTER JOIN settlement_observations so
        ON s.block_number = so.block_number
        AND s.log_index = so.log_index
    WHERE
        ss.block_deadline >= {{start_block}}
        AND ss.block_deadline <= {{end_block}}
),
auction_participation as (
    SELECT
        ap.auction_id,
        array_agg(concat('0x', encode(participant, 'hex'))) as participating_solvers
    FROM
        batch_data_raw
        JOIN  auction_participants ap
        ON ap.auction_id = batch_data_raw.auction_id
    GROUP BY
        ap.auction_id
)
SELECT
    *
FROM batch_data_raw
JOIN auction_participation
USING (auction_id)
