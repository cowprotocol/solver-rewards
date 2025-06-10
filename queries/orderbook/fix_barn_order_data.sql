CREATE TEMP TABLE tmp_order_data (
    environment TEXT,
    auction_id BIGINT,
    order_uid TEXT,
    block_number BIGINT,
    solver TEXT,
    quote_solver TEXT,
    tx_hash TEXT,
    surplus_fee TEXT,
    amount DOUBLE PRECISION,
    protocol_fee TEXT,
    protocol_fee_token TEXT,
    protocol_fee_native_price DOUBLE PRECISION,
    quote_sell_amount TEXT,
    quote_buy_amount TEXT,
    quote_gas_cost DOUBLE PRECISION,
    quote_sell_token_price DOUBLE PRECISION,
    partner_fee TEXT,
    partner_fee_recipient TEXT,
    protocol_fee_kind TEXT
)

--

