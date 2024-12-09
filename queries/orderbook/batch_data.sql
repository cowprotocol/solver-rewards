WITH observed_settlements AS (
    SELECT
        -- settlement
        tx_hash,
        solver,
        s.block_number,
        -- settlement_observations
        effective_gas_price * gas_used AS execution_cost,
        surplus,
        s.auction_id
    FROM
        settlement_observations so
        JOIN settlements s ON s.block_number = so.block_number
        AND s.log_index = so.log_index
        JOIN settlement_scores ss ON s.auction_id = ss.auction_id
    WHERE
        ss.block_deadline > {{start_block}}
        AND ss.block_deadline <= {{end_block}}
),
-- order data
order_data AS (
    SELECT
        uid,
        sell_token,
        buy_token,
        sell_amount,
        buy_amount,
        kind,
        app_data
    FROM orders
    UNION ALL
    SELECT
        uid,
        sell_token,
        buy_token,
        sell_amount,
        buy_amount,
        kind,
        app_data
    FROM jit_orders
),
-- unprocessed trade data
trade_data_unprocessed AS (
    SELECT
        ss.winner AS solver,
        s.auction_id,
        s.tx_hash,
        t.order_uid,
        od.sell_token,
        od.buy_token,
        t.sell_amount, -- the total amount the user sends
        t.buy_amount, -- the total amount the user receives
        oe.surplus_fee AS observed_fee, -- the total discrepancy between what the user sends and what they would have send if they traded at clearing price
        od.kind,
        CASE
            WHEN od.kind = 'sell' THEN od.buy_token
            WHEN od.kind = 'buy' THEN od.sell_token
        END AS surplus_token,
        convert_from(ad.full_app_data, 'UTF8')::JSONB->'metadata'->'partnerFee'->>'recipient' AS partner_fee_recipient,
        COALESCE(oe.protocol_fee_amounts[1], 0) AS first_protocol_fee_amount,
        COALESCE(oe.protocol_fee_amounts[2], 0) AS second_protocol_fee_amount
    FROM
        settlements s
        JOIN settlement_scores ss -- contains block_deadline
        ON s.auction_id = ss.auction_id
        JOIN trades t -- contains traded amounts
        ON s.block_number = t.block_number -- given the join that follows with the order execution table, this works even when multiple txs appear in the same block
        JOIN order_data od -- contains tokens and limit amounts
        ON t.order_uid = od.uid
        JOIN order_execution oe -- contains surplus fee
        ON t.order_uid = oe.order_uid
        AND s.auction_id = oe.auction_id
        LEFT OUTER JOIN app_data ad -- contains full app data
        ON od.app_data = ad.contract_app_data
    WHERE
        ss.block_deadline > {{start_block}}
        AND ss.block_deadline <= {{end_block}}
),
-- processed trade data:
trade_data_processed AS (
    SELECT
        auction_id,
        solver,
        tx_hash,
        order_uid,
        sell_amount,
        buy_amount,
        sell_token,
        observed_fee,
        surplus_token,
        second_protocol_fee_amount,
        first_protocol_fee_amount + second_protocol_fee_amount AS protocol_fee,
        partner_fee_recipient,
        CASE
            WHEN partner_fee_recipient IS NOT NULL THEN second_protocol_fee_amount
            ELSE 0
        END AS partner_fee,
        surplus_token AS protocol_fee_token
    FROM
        trade_data_unprocessed
),
price_data AS (
    SELECT
        tdp.auction_id,
        tdp.order_uid,
        ap_surplus.price / pow(10, 18) AS surplus_token_native_price,
        ap_protocol.price / pow(10, 18) AS protocol_fee_token_native_price,
        ap_sell.price / pow(10, 18) AS network_fee_token_native_price
    FROM
        trade_data_processed AS tdp
        LEFT OUTER JOIN auction_prices ap_sell -- contains price: sell token
        ON tdp.auction_id = ap_sell.auction_id
        AND tdp.sell_token = ap_sell.token
        LEFT OUTER JOIN auction_prices ap_surplus -- contains price: surplus token
        ON tdp.auction_id = ap_surplus.auction_id
        AND tdp.surplus_token = ap_surplus.token
        LEFT OUTER JOIN auction_prices ap_protocol -- contains price: protocol fee token
        ON tdp.auction_id = ap_protocol.auction_id
        AND tdp.surplus_token = ap_protocol.token
),
trade_data_processed_with_prices AS (
    SELECT
        tdp.auction_id,
        tdp.solver,
        tdp.tx_hash,
        tdp.order_uid,
        tdp.surplus_token,
        tdp.protocol_fee,
        tdp.protocol_fee_token,
        tdp.partner_fee,
        tdp.partner_fee_recipient,
        CASE
            WHEN tdp.sell_token != tdp.surplus_token THEN tdp.observed_fee - (tdp.sell_amount - tdp.observed_fee) / tdp.buy_amount * COALESCE(tdp.protocol_fee, 0)
            ELSE tdp.observed_fee - COALESCE(tdp.protocol_fee, 0)
        END AS network_fee,
        tdp.sell_token AS network_fee_token,
        surplus_token_native_price,
        protocol_fee_token_native_price,
        network_fee_token_native_price
    FROM
        trade_data_processed AS tdp
        JOIN price_data pd
        ON tdp.auction_id = pd.auction_id
        AND tdp.order_uid = pd.order_uid
),
batch_protocol_fees AS (
    SELECT
        solver,
        tx_hash,
        sum(protocol_fee * protocol_fee_token_native_price) AS protocol_fee
    FROM
        trade_data_processed_with_prices
    GROUP BY
        solver,
        tx_hash
),
batch_network_fees AS (
    SELECT
        solver,
        tx_hash,
        sum(network_fee * network_fee_token_native_price) AS network_fee
    FROM
        trade_data_processed_with_prices
    GROUP BY
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
        ss.winner as solver,
        block_number as settlement_block,
        block_deadline,
        coalesce(execution_cost, 0) as execution_cost,
        coalesce(surplus, 0) as surplus,
        -- scores
        winning_score,
        case
            when block_number is not null
            and block_number <= block_deadline + 1 then winning_score -- this includes a grace period of one block for settling a batch
            else 0
        end as observed_score,
        reference_score,
        -- protocol_fees
        coalesce(cast(protocol_fee as numeric(78, 0)), 0) as protocol_fee,
        coalesce(
            cast(network_fee as numeric(78, 0)),
            0
        ) as network_fee
    FROM
        settlement_scores ss
        -- outer joins made in order to capture non-existent settlements.
        LEFT OUTER JOIN observed_settlements os ON os.auction_id = ss.auction_id
        LEFT OUTER JOIN batch_protocol_fees bpf ON bpf.tx_hash = os.tx_hash
        LEFT OUTER JOIN batch_network_fees bnf ON bnf.tx_hash = os.tx_hash
        WHERE
            ss.block_deadline > {{start_block}}
            AND ss.block_deadline <= {{end_block}}
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
        network_fee, -- the network fee
        observed_score - reference_score as uncapped_payment,
        -- Capped Reward = CLAMP_[-E, E + exec_cost](uncapped_reward_eth)
        LEAST(
            GREATEST(
                - 10000000000000000000,
                observed_score - reference_score
            ),
            20000000000000000000
        ) as capped_payment,
        winning_score,
        reference_score
    FROM
        reward_data
)
SELECT
    '{{env}}' as environment,
    auction_id,
    settlement_block as block_number,
    block_deadline,
    case
        when tx_hash is NULL then NULL
        else concat('0x', encode(tx_hash, 'hex'))
    end as tx_hash,
    solver,
    execution_cost,
    surplus,
    protocol_fee,
    network_fee,
    uncapped_payment as uncapped_payment_eth,
    capped_payment,
    winning_score,
    reference_score
FROM
    reward_per_auction
ORDER BY block_deadline
