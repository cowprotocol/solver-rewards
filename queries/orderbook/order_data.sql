with trade_hashes as (
    SELECT
        settlement.solver,
        t.block_number as block_number,
        order_uid,
        fee_amount,
        settlement.tx_hash,
        auction_id
    FROM
        trades t
        LEFT OUTER JOIN LATERAL (
            SELECT
                tx_hash,
                solver,
                tx_nonce,
                tx_from,
                auction_id,
                block_number,
                log_index
            FROM
                settlements s
            WHERE
                s.block_number = t.block_number
                AND s.log_index > t.log_index
            ORDER BY
                s.log_index ASC
            LIMIT
                1
        ) AS settlement ON true
        join settlement_observations so on settlement.block_number = so.block_number
        and settlement.log_index = so.log_index
    where
        settlement.block_number >= {{start_block}}
        and settlement.block_number <= {{end_block}}
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
protocol_fee_kind AS (
    SELECT DISTINCT ON (fp.auction_id, fp.order_uid)
        fp.auction_id,
        fp.order_uid,
        fp.kind
    FROM fee_policies fp
        JOIN trade_hashes th
        ON fp.auction_id = th.auction_id AND fp.order_uid = th.order_uid
    ORDER BY fp.auction_id, fp.order_uid, fp.application_order
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
        s.block_number >= {{start_block}}
        AND s.block_number <= {{end_block}}
),
-- processed trade data:
trade_data_processed AS (
    SELECT
        tdu.auction_id,
        tdu.solver,
        tdu.tx_hash,
        tdu.order_uid,
        tdu.sell_amount,
        tdu.buy_amount,
        tdu.sell_token,
        tdu.observed_fee,
        tdu.surplus_token,
        tdu.second_protocol_fee_amount,
        tdu.first_protocol_fee_amount + tdu.second_protocol_fee_amount AS protocol_fee,
        tdu.partner_fee_recipient,
        CASE
            WHEN tdu.partner_fee_recipient IS NOT NULL THEN tdu.second_protocol_fee_amount
            ELSE 0
        END AS partner_fee,
        tdu.surplus_token AS protocol_fee_token,
        pfk.kind as protocol_fee_kind
    FROM
        trade_data_unprocessed tdu
            LEFT OUTER JOIN protocol_fee_kind pfk
            ON tdu.order_uid = pfk.order_uid AND tdu.auction_id = pfk.auction_id 
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
        network_fee_token_native_price,
        protocol_fee_kind
    FROM
        trade_data_processed AS tdp
        JOIN price_data pd
        ON tdp.auction_id = pd.auction_id
        AND tdp.order_uid = pd.order_uid
),
winning_quotes as (
    SELECT
        concat('0x', encode(oq.solver, 'hex')) as quote_solver,
        oq.order_uid
    FROM
        trades t
        INNER JOIN orders o ON order_uid = uid
        JOIN order_quotes oq ON t.order_uid = oq.order_uid
    WHERE
        (
            o.class = 'market'
            OR (
                o.kind = 'sell'
                AND (
                    oq.sell_amount - oq.gas_amount * oq.gas_price / oq.sell_token_price
                ) * oq.buy_amount >= o.buy_amount * oq.sell_amount
            )
            OR (
                o.kind = 'buy'
                AND o.sell_amount >= oq.sell_amount + oq.gas_amount * oq.gas_price / oq.sell_token_price
            )
        )
        AND o.partially_fillable = 'f' -- the code above might fail for partially fillable orders
        AND t.block_number >= {{start_block}}
        AND t.block_number <= {{end_block}}
        AND oq.solver != '\x0000000000000000000000000000000000000000'
) -- Most efficient column order for sorting would be having tx_hash or order_uid first
select
    '{{env}}' as environment,
    trade_hashes.auction_id as auction_id,
    trade_hashes.block_number as block_number,
    concat('0x', encode(trade_hashes.order_uid, 'hex')) as order_uid,
    concat('0x', encode(trade_hashes.solver, 'hex')) as solver,
    quote_solver,
    concat('0x', encode(trade_hashes.tx_hash, 'hex')) as tx_hash,
    coalesce(surplus_fee, 0) :: text as surplus_fee,
    coalesce(reward, 0.0) as amount,
    coalesce(cast(protocol_fee as numeric(78, 0)), 0) :: text as protocol_fee,
    CASE
        WHEN protocol_fee_token is not NULL THEN concat('0x', encode(protocol_fee_token, 'hex'))
    END as protocol_fee_token,
    coalesce(protocol_fee_token_native_price, 0.0) as protocol_fee_native_price,
    cast(oq.sell_amount as numeric(78, 0)) :: text  as quote_sell_amount,
    cast(oq.buy_amount as numeric(78, 0)) :: text as quote_buy_amount,
    oq.gas_amount * oq.gas_price as quote_gas_cost,
    oq.sell_token_price as quote_sell_token_price,
    cast(coalesce(tdpwp.partner_fee, 0) as numeric(78, 0)) :: text as partner_fee,
    tdpwp.partner_fee_recipient,
    tdpwp.protocol_fee_kind
from
    trade_hashes
    left outer join order_execution o on trade_hashes.order_uid = o.order_uid
    and trade_hashes.auction_id = o.auction_id
    left outer join winning_quotes wq on trade_hashes.order_uid = wq.order_uid
    left outer join trade_data_processed_with_prices tdpwp on trade_hashes.order_uid = tdpwp.order_uid
    and trade_hashes.auction_id = tdpwp.auction_id
    left outer join order_quotes oq on trade_hashes.order_uid = oq.order_uid
    order by trade_hashes.block_number asc
