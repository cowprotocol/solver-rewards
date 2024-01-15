WITH order_surplus AS (
    SELECT
        ss.winner as solver,
        at.auction_id,
        t.order_uid,
        o.sell_token, -- the total amount the user sends
        o.buy_token,
        t.sell_amount,
        t.buy_amount,
        oe.surplus_fee as observed_fee,
        o.kind,
        CASE
            WHEN o.kind = 'sell'
                THEN t.buy_amount - o.buy_amount / (o.sell_amount + o.fee_amount) * t.sell_amount
            WHEN o.kind = 'buy'
                THEN (o.sell_amount + o.fee_amount) / o.buy_amount * t.buy_amount - t.sell_amount
        END AS surplus,
        CASE
            WHEN o.kind = 'sell'
                THEN o.buy_token
            WHEN o.kind = 'buy'
                THEN o.sell_token
        END AS surplus_token
    FROM settlements s -- links block_number and log_index to tx_from and tx_nonce
    JOIN auction_transaction at -- links auction_id to tx_from and tx_nonce
        ON s.tx_from = at.tx_from AND s.tx_nonce = at.tx_nonce
    JOIN settlement_scores ss -- contains block_deadline
        ON at.auction_id = ss.auction_id
    JOIN trades t -- contains traded amounts
        ON s.block_number = t.block_number -- log_index cannot be checked, does not work correctly with multiple auctions on the same block
    JOIN orders o -- contains tokens and limit amounts
        ON t.order_uid = o.uid
    JOIN order_execution oe -- contains surplus fee
        ON t.order_uid = oe.order_uid AND at.auction_id = oe.auction_id
    WHERE ss.block_deadline > 0
        AND ss.block_deadline <= 100
)
,order_observation AS (
    SELECT
        os.auction_id,
        os.solver,
        os.sell_amount, -- the total amount the user sends
        os.buy_amount,
        os.sell_token,
        os.observed_fee,
        os.surplus,
        os.surplus_token,
        CASE
            WHEN fp.kind = 'surplus'
                THEN
                    CASE
                        WHEN os.kind = 'sell'
                            THEN
                                LEAST(
                                    fp.max_volume_factor / (1 - fp.max_volume_factor) * os.buy_amount, -- at most charge a fraction of volume
                                    fp.surplus_factor / (1 - fp.surplus_factor) * surplus -- charge a fraction of surplus
                                )
                        WHEN os.kind = 'buy'
                            THEN
                                LEAST(
                                    fp.max_volume_factor / (1 - fp.max_volume_factor) * os.sell_amount, -- at most charge a fraction of volume
                                    fp.surplus_factor / (1 - fp.surplus_factor) * surplus -- charge a fraction of surplus
                                )
                    END
            WHEN fp.kind = 'volume'
                THEN fp.volume_factor / (1 - fp.volume_factor) * os.sell_amount
        END AS protocol_fee,
        CASE
            WHEN fp.kind = 'surplus'
                THEN os.surplus_token
            WHEN fp.kind = 'volume'
                THEN os.sell_token
        END AS protocol_fee_token
    FROM order_surplus os
    JOIN fee_policies fp -- contains protocol fee policy
        ON os.auction_id = fp.auction_id AND os.order_uid = fp.order_uid
)
,order_observations_prices AS (
    SELECT
        oo.solver,
        oo.surplus,
        oo.protocol_fee,
        CASE
            WHEN oo.sell_token != oo.protocol_fee_token
                THEN oo.observed_fee - (oo.sell_amount - oo.observed_fee) / oo.buy_amount * oo.protocol_fee
            ELSE oo.observed_fee - oo.protocol_fee
        END AS network_fee,
        oo.sell_token as network_fee_token,
        ap_surplus.price / pow(10, 18) as surplus_token_price,
        ap_protocol.price / pow(10, 18) as protocol_fee_token_price,
        ap_sell.price / pow(10, 18) as network_fee_token_price
    FROM order_observation oo
    JOIN auction_prices ap_sell -- contains price: sell token
        ON oo.auction_id = ap_sell.auction_id AND oo.sell_token = ap_sell.token
    JOIN auction_prices ap_surplus -- contains price: surplus token
        ON oo.auction_id = ap_surplus.auction_id AND oo.surplus_token = ap_surplus.token
    JOIN auction_prices ap_protocol -- contains price: protocol fee token
        ON oo.auction_id = ap_protocol.auction_id AND oo.protocol_fee_token = ap_protocol.token
),
batch_aggregate AS (
    SELECT
        concat('0x', encode(solver, 'hex')) as solver,
        -- sum(surplus * surplus_token_price) as surplus,
        sum(protocol_fee * protocol_fee_token_price) as protocol_fee,
        sum(network_fee * network_fee_token_price) as network_fee
    FROM order_observations_prices oop
    group by solver
)
SELECT * FROM batch_aggregate
