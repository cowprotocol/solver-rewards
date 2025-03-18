-- this table excludes certain accounts due to wash-trading
excluded_quotes as ( --noqa: PRS
    select uid as order_uid
    from orders
    where
        -- wash-trading USDC/DAI on mainnet
        owner = '\x687f584fd1f4a4d9eb277c03a24fe28f4b0675b7'
        and
        (
            (sell_token = '\xa0b86991c6218b36c1d19d4a2e9eb0ce3606eb48' and buy_token = '\x6b175474e89094c44da98b954eedeac495271d0f')
            or
            (buy_token = '\xa0b86991c6218b36c1d19d4a2e9eb0ce3606eb48' and sell_token = '\x6b175474e89094c44da98b954eedeac495271d0f')
        )
),
