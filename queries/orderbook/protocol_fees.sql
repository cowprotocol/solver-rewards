-- Active: 1704993022452@@127.0.0.1@5432@postgres@public
-- Active: 1704193756200@@cow-protocol-db-read-replica.c5bze0gkehvb.eu-central-1.rds.amazonaws.com@5432@mainnet@public
WITH order_surplus AS (
    SELECT
        at.auction_id,
        s.tx_hash,
        t.order_uid,
        o.sell_token,
        o.buy_token,
        t.sell_amount,
        t.buy_amount,
        oe.surplus_fee,
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
        END AS surplus_token,
        CASE
            WHEN o.kind = 'sell'
                THEN
                    t.buy_amount - oq.buy_amount / (o.sell_amount + o.fee_amount) * t.sell_amount
            WHEN o.kind = 'buy'
                THEN
                    (oq.sell_amount + o.fee_amount) / o.buy_amount * t.buy_amount - t.sell_amount
        END AS price_improvement
    FROM settlements s -- links block_number and log_index to tx_from and tx_nonce
    JOIN auction_transaction at -- links auction_id to tx_from and tx_nonce
        ON s.tx_from = at.tx_from AND s.tx_nonce = at.tx_nonce
    JOIN settlement_scores ss -- contains block_deadline
        ON at.auction_id = ss.auction_id
    JOIN trades t -- contains traded amounts
        ON s.block_number = t.block_number -- log_index cannot be checked, does not work correctly with multiple auctions on the same block
    JOIN orders o -- contains tokens and limit amounts
        ON t.order_uid = o.uid
    JOIN order_executions oe -- contains surplus fee
        ON t.order_uid = oe.order_uid AND at.auction_id = oe.auction_id
    JOIN order_quotes oq -- contains quote
        ON t.order_uid = oq.order_uid
    WHERE ss.block_deadline > 0
        AND ss.block_deadline <= 100
)
,protocol_fees_raw AS (
    SELECT
        os.*, -- TODO: select data
        CASE
            WHEN fp.kind = 'priceimprovement'
                THEN
                    CASE
                        WHEN os.kind = 'sell'
                            THEN
                                GREATEST(
                                    0, -- never charge a negative amount
                                    LEAST(
                                        fp.max_volume_factor / (1 - fp.max_volume_factor) * os.buy_amount, -- at most charge a fraction of volume
                                        fp.price_improvement_factor * LEAST(price_improvement, surplus) -- charge a fraction of price improvement
                                    )
                                )
                        WHEN os.kind = 'buy'
                            THEN
                                GREATEST(
                                    0, -- never charge a negative amount
                                    LEAST(
                                        fp.max_volume_factor / (1 - fp.max_volume_factor) * os.sell_amount, -- at most charge a fraction of volume
                                        fp.price_improvement_factor / (1 - fp.price_improvement_factor) * LEAST(price_improvement, surplus) -- charge a fraction of price improvement
                                    )
                                )
                    END
            WHEN fp.kind = 'volume'
                THEN fp.volume_factor / (1 - fp.volume_factor) * os.sell_amount
        END AS protocol_fee,
        CASE
            WHEN fp.kind = 'priceimprovement'
                THEN os.surplus_token
            WHEN fp.kind = 'volume'
                THEN os.sell_token
        END AS protocol_fee_token
    FROM order_surplus os
    JOIN fee_policies fp -- contains protocol fee policy
        ON os.auction_id = fp.auction_id AND os.order_uid = fp.order_uid
)
,order_fees AS (
    SELECT
        pfr.*, -- TODO: select data
        ap_sell.price as sell_token_price,
        ap_protocol.price as protocol_fee_token_price,
        CASE
            WHEN pfr.sell_token != pfr.protocol_fee_token
                THEN ap_sell.price / pow(10, 18) * (pfr.surplus_fee - (pfr.sell_amount - pfr.surplus_fee) / pfr.buy_amount * pfr.protocol_fee)
            ELSE ap_sell.price / pow(10, 18) * (pfr.surplus_fee - pfr.protocol_fee)
        END AS network_fee
    FROM protocol_fees_raw pfr
    JOIN auction_prices ap_sell -- contains prices
        ON pfr.auction_id = ap_sell.auction_id AND pfr.sell_token = ap_sell.token
    JOIN auction_prices ap_protocol -- contains prices
        ON pfr.auction_id = ap_protocol.auction_id AND pfr.protocol_fee_token = ap_protocol.token
)
select * from order_fees
