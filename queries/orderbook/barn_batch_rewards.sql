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
            WHEN o.kind = 'sell' THEN t.buy_amount - t.sell_amount * (oq.buy_amount - oq.buy_amount / oq.sell_amount * oq.gas_amount * oq.gas_price / oq.sell_token_price) / oq.sell_amount
            WHEN o.kind = 'buy' THEN t.buy_amount * (oq.sell_amount + oq.gas_amount * oq.gas_price / oq.sell_token_price) / oq.buy_amount - t.sell_amount
        END AS price_improvement,
        CASE
            WHEN o.kind = 'sell' THEN o.buy_token
            WHEN o.kind = 'buy' THEN o.sell_token
        END AS surplus_token,
        ad.full_app_data as app_data
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
        LEFT OUTER JOIN order_quotes oq -- contains quote amounts
        ON o.uid = oq.order_uid
        LEFT OUTER JOIN app_data ad -- contains full app data
        on o.app_data = ad.contract_app_data
    WHERE
        ss.block_deadline >= {{start_block}}
        AND ss.block_deadline <= {{end_block}}
),
fee_policies_first_proxy as (
    select
        auction_id,
        order_uid,
        max(application_order) as application_order,
        count (*) as num_policies
    from fee_policies
    where auction_id in (select auction_id from order_surplus)
    group by order_uid, auction_id
),
fee_policies_first as (
    select
        fp.auction_id,
        fp.order_uid,
        fp.application_order,
        fp.kind,
        fp.surplus_factor,
        fp.surplus_max_volume_factor,
        fp.volume_factor,
        fp.price_improvement_factor,
        fp.price_improvement_max_volume_factor
    from fee_policies_first_proxy fpmp join fee_policies fp on fp.auction_id = fpmp.auction_id and fp.order_uid = fpmp.order_uid and fp.application_order = fpmp.application_order
),
fee_policies_temp as (
    select
        *
    from fee_policies
    where auction_id in (select auction_id from order_surplus)
    except (select * from fee_policies_first )
),
fee_policies_second as (
    select
        *
    from fee_policies_temp
    UNION
    select
        auction_id,
        order_uid,
        0 as application_order,
        'volume' as kind,
        null as surplus_factor,
        null as surplus_max_volume_factor,
        0 as volume_factor,
        null as price_improvement_factor,
        null as price_improvement_max_volume_factor
    from fee_policies_first_proxy where num_policies = 1
),
order_protocol_fee_first AS (
    SELECT
        os.auction_id,
        os.order_uid,
        os.sell_amount,
        os.buy_amount,
        os.surplus,
        os.price_improvement,
        os.kind,
        convert_from(os.app_data, 'UTF8')::JSONB->'metadata'->'partnerFee'->>'recipient' as partner_fee_recipient,
        fp.kind as protocol_fee_kind_first,
        CASE
            WHEN fp.kind = 'surplus' THEN CASE
                WHEN os.kind = 'sell' THEN
                -- We assume that the case surplus_factor != 1 always. In
                -- that case reconstructing the protocol fee would be
                -- impossible anyways. This query will return a division by
                -- zero error in that case.
                LEAST(
                    fp.surplus_max_volume_factor / (1 - fp.surplus_max_volume_factor) * os.buy_amount,
                    -- at most charge a fraction of volume
                    fp.surplus_factor / (1 - fp.surplus_factor) * surplus -- charge a fraction of surplus
                )
                WHEN os.kind = 'buy' THEN LEAST(
                    fp.surplus_max_volume_factor / (1 + fp.surplus_max_volume_factor) * os.sell_amount,
                    -- at most charge a fraction of volume
                    fp.surplus_factor / (1 - fp.surplus_factor) * surplus -- charge a fraction of surplus
                )
            END
            WHEN fp.kind = 'priceimprovement' THEN CASE
                WHEN os.kind = 'sell' THEN
                LEAST(
                    -- at most charge a fraction of volume
                    fp.price_improvement_max_volume_factor / (1 - fp.price_improvement_max_volume_factor) * os.buy_amount,
                    -- charge a fraction of price improvement, at most 0
                    GREATEST(
                        fp.price_improvement_factor / (1 - fp.price_improvement_factor) * price_improvement
                        ,
                        0
                    )
                )
                WHEN os.kind = 'buy' THEN LEAST(
                    -- at most charge a fraction of volume
                    fp.price_improvement_max_volume_factor / (1 + fp.price_improvement_max_volume_factor) * os.sell_amount,
                    -- charge a fraction of price improvement
                    GREATEST(
                        fp.price_improvement_factor / (1 - fp.price_improvement_factor) * price_improvement,
                        0
                    )
                )
            END
            WHEN fp.kind = 'volume' THEN CASE
                WHEN os.kind = 'sell' THEN
                    fp.volume_factor / (1 - fp.volume_factor) * os.buy_amount
                WHEN os.kind = 'buy' THEN
                    fp.volume_factor / (1 + fp.volume_factor) * os.sell_amount
            END
        END AS protocol_fee_first,
        os.surplus_token AS protocol_fee_token
    FROM
        order_surplus os
        JOIN fee_policies_first fp -- contains protocol fee policy
        ON os.auction_id = fp.auction_id
        AND os.order_uid = fp.order_uid
),
order_surplus_intermediate as (
    select
        auction_id,
        order_uid,
        CASE
            WHEN kind = 'sell' then sell_amount
            ELSE sell_amount - protocol_fee_first
        END as sell_amount,
        CASE
            WHEN kind = 'sell' then buy_amount + protocol_fee_first
            ELSE buy_amount
        END as buy_amount,
        surplus + protocol_fee_first as surplus,
        price_improvement + protocol_fee_first as price_improvement,
        protocol_fee_kind_first,
        protocol_fee_first,
        partner_fee_recipient
    from order_protocol_fee_first
),
order_protocol_fee as (
    SELECT
        os.auction_id,
        os.solver,
        os.tx_hash,
        os.order_uid,
        os.sell_amount,
        os.buy_amount,
        os.sell_token,
        os.observed_fee,
        os.surplus,
        os.surplus_token,
        protocol_fee_kind_first,
        fp.kind as protocol_fee_kind_second,
        protocol_fee_first,
        CASE
            WHEN fp.kind = 'surplus' THEN CASE
                WHEN os.kind = 'sell' THEN
                -- We assume that the case surplus_factor != 1 always. In
                -- that case reconstructing the protocol fee would be
                -- impossible anyways. This query will return a division by
                -- zero error in that case.
                protocol_fee_first + LEAST(
                    fp.surplus_max_volume_factor / (1 - fp.surplus_max_volume_factor) * osi.buy_amount,
                    -- at most charge a fraction of volume
                    fp.surplus_factor / (1 - fp.surplus_factor) * osi.surplus -- charge a fraction of surplus
                )
                WHEN os.kind = 'buy' THEN protocol_fee_first + LEAST(
                    fp.surplus_max_volume_factor / (1 + fp.surplus_max_volume_factor) * osi.sell_amount,
                    -- at most charge a fraction of volume
                    fp.surplus_factor / (1 - fp.surplus_factor) * osi.surplus -- charge a fraction of surplus
                )
            END
            WHEN fp.kind = 'priceimprovement' THEN CASE
                WHEN os.kind = 'sell' THEN
                protocol_fee_first + LEAST(
                    -- at most charge a fraction of volume
                    fp.price_improvement_max_volume_factor / (1 - fp.price_improvement_max_volume_factor) * osi.buy_amount,
                    -- charge a fraction of price improvement, at most 0
                    GREATEST(
                        fp.price_improvement_factor / (1 - fp.price_improvement_factor) * osi.price_improvement
                        ,
                        0
                    )
                )
                WHEN os.kind = 'buy' THEN protocol_fee_first + LEAST(
                    -- at most charge a fraction of volume
                    fp.price_improvement_max_volume_factor / (1 + fp.price_improvement_max_volume_factor) * osi.sell_amount,
                    -- charge a fraction of price improvement
                    GREATEST(
                        fp.price_improvement_factor / (1 - fp.price_improvement_factor) * osi.price_improvement,
                        0
                    )
                )
            END
            WHEN fp.kind = 'volume' THEN CASE
                WHEN os.kind = 'sell' THEN
                    protocol_fee_first + fp.volume_factor / (1 - fp.volume_factor) * osi.buy_amount
                WHEN os.kind = 'buy' THEN
                    protocol_fee_first + fp.volume_factor / (1 + fp.volume_factor) * osi.sell_amount
            END
        END AS protocol_fee,
        osi.partner_fee_recipient,
        CASE
            WHEN osi.partner_fee_recipient IS NOT NULL THEN osi.protocol_fee_first
            ELSE 0
        END AS partner_fee,
        os.surplus_token AS protocol_fee_token
    FROM
        order_surplus os
        JOIN order_surplus_intermediate osi
        ON os.order_uid = osi.order_uid AND os.auction_id = osi.auction_id
        JOIN fee_policies_second fp -- contains protocol fee policy
        ON os.auction_id = fp.auction_id
        AND os.order_uid = fp.order_uid
),
order_protocol_fee_prices AS (
    SELECT
        opf.auction_id,
        opf.solver,
        opf.tx_hash,
        opf.order_uid,
        opf.surplus,
        opf.protocol_fee,
        opf.protocol_fee_token,
        CASE
            WHEN opf.partner_fee_recipient IS NOT NULL THEN opf.protocol_fee_kind_second
            ELSE opf.protocol_fee_kind_first
        END AS protocol_fee_kind,
        opf.partner_fee,
        opf.partner_fee_recipient,
        CASE
            WHEN opf.sell_token != opf.protocol_fee_token THEN (opf.sell_amount - opf.observed_fee) / opf.buy_amount * opf.protocol_fee
            ELSE opf.protocol_fee
        END AS network_fee_correction,
        opf.sell_token as network_fee_token,
        ap_surplus.price / pow(10, 18) as surplus_token_native_price,
        ap_protocol.price / pow(10, 18) as protocol_fee_token_native_price,
        ap_sell.price / pow(10, 18) as network_fee_token_native_price
    FROM
        order_protocol_fee as opf
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
        sum(protocol_fee * protocol_fee_token_native_price) as protocol_fee,
        sum(network_fee_correction * network_fee_token_native_price) as network_fee_correction
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
            else coalesce(execution_cost, 0) -- if block_number is null, execution cost is 0
        end as execution_cost,
        case
            when block_number is not null
            and block_number > block_deadline then 0
            else coalesce(surplus, 0) -- if block_number is null, surplus is 0
        end as surplus,
        case
            when block_number is not null
            and block_number > block_deadline then 0
            else coalesce(fee, 0) -- if block_number is null, fee is 0
        end as fee,
        -- scores
        winning_score,
        case
            when block_number is not null
            and block_number <= block_deadline then winning_score
            else 0
        end as observed_score,
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
        settlement_scores ss
        -- If there are reported scores,
        -- there will always be a record of auction participants
        JOIN auction_participation ap ON ss.auction_id = ap.auction_id
        -- outer joins made in order to capture non-existent settlements.
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
        observed_score - reference_score as uncapped_payment,
        -- Capped Reward = CLAMP_[-E, E + exec_cost](uncapped_reward_eth)
        LEAST(
            GREATEST(
                - {{EPSILON_LOWER}},
                observed_score - reference_score
            ),
            {{EPSILON_UPPER}}
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
        block_deadline,
        unnest(participating_solvers) as participant
    FROM
        reward_per_auction
),
participation_data_intermediate as (
    SELECT
        tx_hash,
        CASE
            WHEN block_deadline <= 20365510 THEN 1  -- final block deadline of accounting week of July 16 - July 23, 2024
            ELSE 0
        END as count_participation,
        participant
    FROM
        participation_data
),
participation_counts as (
    SELECT
        participant as solver,
        sum(count_participation) as num_participating_batches
    FROM
        participation_data_intermediate
    GROUP BY
        participant
),
primary_rewards as (
    SELECT
        rpt.solver,
        SUM(capped_payment) as payment,
        SUM(protocol_fee) as protocol_fee,
        SUM(network_fee) as network_fee
    FROM
        reward_per_auction rpt
    GROUP BY
        solver
),
partner_fees_per_solver AS (
    SELECT
        solver,
        partner_fee_recipient,
        sum(partner_fee * protocol_fee_token_native_price) as partner_fee
    FROM
        order_protocol_fee_prices
        WHERE partner_fee_recipient is not null
        group by solver,partner_fee_recipient
),
aggregate_partner_fees_per_solver AS (
    SELECT
        solver,
        array_agg(partner_fee_recipient) as partner_list,
        array_agg(partner_fee) as partner_fee
    FROM partner_fees_per_solver
        group by solver
),
aggregate_results as (
    SELECT
        concat('0x', encode(pc.solver, 'hex')) as solver,
        coalesce(payment, 0) as primary_reward_eth,
        num_participating_batches,
        coalesce(protocol_fee, 0) as protocol_fee_eth,
        coalesce(network_fee, 0) as network_fee_eth,
        partner_list,
        partner_fee as partner_fee_eth
    FROM
        participation_counts pc
        LEFT OUTER JOIN primary_rewards pr ON pr.solver = pc.solver
        LEFT OUTER JOIN aggregate_partner_fees_per_solver aif on pr.solver = aif.solver 
) --
select
    *
from
    aggregate_results
order by
    solver
