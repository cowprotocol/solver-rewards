WITH trade_data_raw AS MATERIALIZED (
    SELECT
        -- settlement data
        concat('0x', encode(ss.winner, 'hex')) AS winning_solver,
        s.auction_id,
        CASE WHEN s.tx_hash IS NULL THEN NULL
            ELSE concat('0x', encode(s.tx_hash, 'hex'))
        END AS tx_hash,
        -- order data
        concat('0x', encode(o.uid, 'hex')) AS order_uid,
        o.kind,
        o.partially_fillable,
        concat('0x', encode(o.sell_token, 'hex')) AS sell_token,
        concat('0x', encode(o.buy_token, 'hex')) AS buy_token,
        o.sell_amount as limit_sell_amount,
        o.buy_amount as limit_buy_amount,
        concat('0x', encode(ad.full_app_data, 'hex')) AS app_data,
        -- quote data
        oq.sell_amount as quote_sell_amount,
        oq.buy_amount as quote_buy_amount,
        oq.gas_amount as quote_gas_amount,
        oq.gas_price as quote_gas_price,
        oq.sell_token_price as quote_sell_token_price,
        CASE WHEN oq.solver IS NULL THEN NULL
            ELSE concat('0x', encode(oq.solver, 'hex'))
        END AS quote_solver,
        -- trade data
        t.sell_amount, -- the total amount the user sends
        t.buy_amount, -- the total amount the user receives
        oe.surplus_fee as observed_fee, -- the total discrepancy between what the user sends and what they would have send if they traded at clearing price
        -- native prices
        ap_sell.price as sell_token_native_price,
        ap_buy.price as buy_token_native_price
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
        LEFT OUTER JOIN app_data ad
        ON o.app_data = ad.contract_app_data 
        LEFT OUTER JOIN auction_prices ap_sell -- contains price: sell token
        ON s.auction_id = ap_sell.auction_id
        AND o.sell_token = ap_sell.token
        LEFT OUTER JOIN auction_prices ap_buy -- contains price: sell token
        ON s.auction_id = ap_buy.auction_id
        AND o.buy_token = ap_buy.token
    WHERE
        ss.block_deadline >= {{start_block}}
        AND ss.block_deadline <= {{end_block}}
),
auction_range AS (
    SELECT
        MIN(auction_id) AS start_auction_id,
        MAX(auction_id) AS end_auction_id
    FROM
        trade_data_raw
),
trades_protocol_fee AS MATERIALIZED (
    SELECT
        auction_id,
        concat('0x', encode(order_uid, 'hex')) AS order_uid,
        array_agg(application_order) as application_order,
        array_agg(kind) as protocol_fee_kind,
        array_agg(surplus_factor) as surplus_factor,
        array_agg(surplus_max_volume_factor) as surplus_max_volume_factor,
        array_agg(volume_factor) as volume_factor,
        array_agg(price_improvement_factor) as price_improvement_factor,
        array_agg(price_improvement_max_volume_factor) as price_improvement_max_volume_factor
    FROM
        fee_policies
    WHERE auction_id between (select start_auction_id from auction_range) and (select end_auction_id from auction_range)
    GROUP BY auction_id, order_uid
)

SELECT
    *
FROM
    trade_data_raw tdr
    LEFT OUTER JOIN trades_protocol_fee tpf
    USING (auction_id, order_uid)
