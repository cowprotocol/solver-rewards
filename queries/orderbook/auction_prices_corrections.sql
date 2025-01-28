auction_price_corrections (blockchain, environment, auction_id, price) as (
    select *
    from (
        values 
        ('ethereum', 'prod', '\x5c47902c8c80779cb99235e42c354e53f38c3b0d'::bytea, 101902651::numeric(78, 0))
    ) as temp(blockchain, environment, auction_id, price)
    where blockchain = '{{blockchain}}' and environment = '{{environment}}'
)
