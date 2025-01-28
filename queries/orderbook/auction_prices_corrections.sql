auction_prices_corrections (blockchain, environment, auction_id, token, price) as ( --noqa: PRS
    select *
    from (
        values 
        ('ethereum', 'prod', 10105124::bigint, '\x5c47902c8c80779cb99235e42c354e53f38c3b0d'::bytea, 101902651::numeric(78, 0))
    ) as temp(blockchain, environment, auction_id, token, price)
    where blockchain = '{{blockchain}}' and environment = '{{environment}}'
),
