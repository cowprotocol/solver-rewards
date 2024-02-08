WITH observed_settlements AS (
    SELECT
        -- settlement
        tx_hash,
        solver,
        s.block_number,
        -- settlement_observations
        effective_gas_price * gas_used AS execution_cost,
        surplus,
        fee,
        s.auction_id
    FROM
        settlement_observations so
        JOIN settlements s ON s.block_number = so.block_number
        AND s.log_index = so.log_index
        JOIN settlement_scores ss ON s.auction_id = ss.auction_id
    WHERE
        ss.block_deadline >= {{start_block}}
        AND ss.block_deadline <= {{end_block}}
),
auction_participation as (
    SELECT
        ss.auction_id,
        array_agg(participant) as participating_solvers
    FROM
        auction_participants
        JOIN settlement_scores ss ON auction_participants.auction_id = ss.auction_id
    WHERE
        block_deadline >= {{start_block}}
        AND block_deadline <= {{end_block}}
    GROUP BY
        ss.auction_id
),
-- protocol fees:
order_surplus AS (
    SELECT
        ss.winner as solver,
        s.auction_id,
        s.tx_hash,
        t.order_uid,
        o.sell_token,
        o.buy_token,
        t.sell_amount, -- the total amount the user sends
        t.buy_amount, -- the total amount the user receives
        oe.surplus_fee as observed_fee, -- the total discrepancy between what the user sends and what they would have send if they traded at clearing price
        o.kind,
        CASE
            WHEN o.kind = 'sell' THEN t.buy_amount - t.sell_amount * o.buy_amount / (o.sell_amount + o.fee_amount)
            WHEN o.kind = 'buy' THEN t.buy_amount * (o.sell_amount + o.fee_amount) / o.buy_amount - t.sell_amount
        END AS surplus,
        CASE
            WHEN o.kind = 'sell' THEN o.buy_token
            WHEN o.kind = 'buy' THEN o.sell_token
        END AS surplus_token
    FROM
        settlements s
        JOIN settlement_scores ss -- contains block_deadline
        ON s.auction_id = ss.auction_id
        JOIN trades t -- contains traded amounts
        ON s.block_number = t.block_number -- log_index cannot be checked, does not work correctly with multiple auctions on the same block
        JOIN orders o -- contains tokens and limit amounts
        ON t.order_uid = o.uid
        JOIN order_execution oe -- contains surplus fee
        ON t.order_uid = oe.order_uid
        AND s.auction_id = oe.auction_id
    WHERE
        ss.block_deadline >= {{start_block}}
        AND ss.block_deadline <= {{end_block}}
),
order_protocol_fee AS (
    SELECT
        os.auction_id,
        os.solver,
        os.tx_hash,
        os.sell_amount,
        os.buy_amount,
        os.sell_token,
        os.observed_fee,
        os.surplus,
        os.surplus_token,
        CASE
            WHEN fp.kind = 'surplus' THEN CASE
                WHEN os.kind = 'sell' THEN
                -- We assume that the case surplus_factor != 1 always. In
                -- that case reconstructing the protocol fee would be
                -- impossible anyways. This query will return a division by
                -- zero error in that case.
                LEAST(
                    fp.max_volume_factor * os.sell_amount * os.buy_amount / (os.sell_amount - os.observed_fee),
                    -- at most charge a fraction of volume
                    fp.surplus_factor / (1 - fp.surplus_factor) * surplus -- charge a fraction of surplus
                )
                WHEN os.kind = 'buy' THEN LEAST(
                    fp.max_volume_factor / (1 + fp.max_volume_factor) * os.sell_amount,
                    -- at most charge a fraction of volume
                    fp.surplus_factor / (1 - fp.surplus_factor) * surplus -- charge a fraction of surplus
                )
            END
            WHEN fp.kind = 'volume' THEN fp.volume_factor / (1 + fp.volume_factor) * os.sell_amount
        END AS protocol_fee,
        CASE
            WHEN fp.kind = 'surplus' THEN os.surplus_token
            WHEN fp.kind = 'volume' THEN os.sell_token
        END AS protocol_fee_token
    FROM
        order_surplus os
        JOIN fee_policies fp -- contains protocol fee policy
        ON os.auction_id = fp.auction_id
        AND os.order_uid = fp.order_uid
),
order_protocol_fee_prices AS (
    SELECT
        opf.solver,
        opf.tx_hash,
        opf.surplus,
        opf.protocol_fee,
        CASE
            WHEN opf.sell_token != opf.protocol_fee_token THEN (opf.sell_amount - opf.observed_fee) / opf.buy_amount * opf.protocol_fee
            ELSE opf.protocol_fee
        END AS network_fee_correction,
        opf.sell_token as network_fee_token,
        ap_surplus.price / pow(10, 18) as surplus_token_price,
        ap_protocol.price / pow(10, 18) as protocol_fee_token_price,
        ap_sell.price / pow(10, 18) as network_fee_token_price
    FROM
        order_protocol_fee opf
        JOIN auction_prices ap_sell -- contains price: sell token
        ON opf.auction_id = ap_sell.auction_id
        AND opf.sell_token = ap_sell.token
        JOIN auction_prices ap_surplus -- contains price: surplus token
        ON opf.auction_id = ap_surplus.auction_id
        AND opf.surplus_token = ap_surplus.token
        JOIN auction_prices ap_protocol -- contains price: protocol fee token
        ON opf.auction_id = ap_protocol.auction_id
        AND opf.protocol_fee_token = ap_protocol.token
),
batch_protocol_fees AS (
    SELECT
        solver,
        tx_hash,
        -- sum(surplus * surplus_token_price) as surplus,
        sum(protocol_fee * protocol_fee_token_price) as protocol_fee,
        sum(network_fee_correction * network_fee_token_price) as network_fee_correction
    FROM
        order_protocol_fee_prices
    group by
        solver,
        tx_hash
),
reward_data AS (
    SELECT
        -- observations
        os.tx_hash,
        ss.auction_id,
        -- TODO - Assuming that `solver == winner` when both not null
        --  We will need to monitor that `solver == winner`!
        coalesce(os.solver, winner) as solver,
        block_number as settlement_block,
        block_deadline,
        case
            when block_number is not null
            and block_number > block_deadline then 0
            else coalesce(execution_cost, 0)
        end as execution_cost,
        case
            when block_number is not null
            and block_number > block_deadline then 0
            else coalesce(surplus, 0)
        end as surplus,
        case
            when block_number is not null
            and block_number > block_deadline then 0
            else coalesce(fee, 0)
        end as fee,
        -- scores
        winning_score,
        reference_score,
        -- auction_participation
        participating_solvers,
        -- protocol_fees
        coalesce(cast(protocol_fee as numeric(78, 0)), 0) as protocol_fee,
        coalesce(
            cast(network_fee_correction as numeric(78, 0)),
            0
        ) as network_fee_correction
    FROM
        settlement_scores ss -- If there are reported scores,
        -- there will always be a record of auction participants
        JOIN auction_participation ap ON ss.auction_id = ap.auction_id -- outer joins made in order to capture non-existent settlements.
        LEFT OUTER JOIN observed_settlements os ON os.auction_id = ss.auction_id
        LEFT OUTER JOIN batch_protocol_fees bpf ON bpf.tx_hash = os.tx_hash
),
reward_per_auction as (
    SELECT
        tx_hash,
        auction_id,
        settlement_block,
        block_deadline,
        solver,
        execution_cost,
        surplus,
        protocol_fee, -- the protocol fee
        fee - network_fee_correction as network_fee, -- the network fee
        surplus + protocol_fee + fee - network_fee_correction - reference_score as uncapped_payment_eth,
        -- Capped Reward = CLAMP_[-E, E + exec_cost](uncapped_reward_eth)
        LEAST(
            GREATEST(
                - {{EPSILON}},
                surplus + protocol_fee + fee - network_fee_correction - reference_score
            ),
            {{EPSILON}} + execution_cost
        ) as capped_payment,
        winning_score,
        reference_score,
        participating_solvers as participating_solvers
    FROM
        reward_data
),
participation_data as (
    SELECT
        tx_hash,
        unnest(participating_solvers) as participant
    FROM
        reward_per_auction
),
participation_counts as (
    SELECT
        participant as solver,
        count(*) as num_participating_batches
    FROM
        participation_data
    GROUP BY
        participant
),
primary_rewards as (
    SELECT
        rpt.solver,
        SUM(capped_payment) as payment_wei,
        SUM(execution_cost) as exececution_cost_wei
    FROM
        reward_per_auction rpt
    GROUP BY
        solver
),
protocol_fees as (
    SELECT
        solver,
        SUM(protocol_fee) as protocol_fee_wei
    FROM
        reward_per_auction rpt
    GROUP BY
        solver
),
aggregate_results as (
    SELECT
        concat('0x', encode(pc.solver, 'hex')) as solver,
        coalesce(payment_wei, 0) as payment_eth,
        coalesce(exececution_cost_wei, 0) as execution_cost_eth,
        num_participating_batches,
        coalesce(protocol_fee_wei, 0) as protocol_fee_eth
    FROM
        participation_counts pc
        LEFT OUTER JOIN primary_rewards pr ON pr.solver = pc.solver
        LEFT OUTER JOIN protocol_fees pf ON pf.solver = pc.solver
) --
select
    *
from
    aggregate_results
order by
    solver