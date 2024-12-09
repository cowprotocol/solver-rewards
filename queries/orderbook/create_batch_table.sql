-- sample table name for creating the intermediate tables used in the analytics db to store batch data
create table raw_batch_data_latest_odd_month_gnosis (
    environment varchar(6) not null,
    auction_id bigint not null,
    settlement_block bigint,
    block_deadline bigint not null,
    tx_hash bytea,
    solver bytea not null,
    execution_cost numeric(78,0),
    surplus numeric(78,0),
    protocol_fee numeric(78,0),
    network_fee numeric(78,0),
    uncapped_payment_native_token numeric(78,0) not null,
    capped_payment  numeric (78,0) not null,
    winning_score numeric(78,0) not null,
    reference_score numeric(78,0) not null,
    PRIMARY KEY (block_deadline, auction_id, environment)
);
