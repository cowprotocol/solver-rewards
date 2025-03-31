-- this table excludes certain accounts due to repetitive trading back and forth
excluded_quotes as ( --noqa: PRS
    select uid as order_uid
    from orders
    where (
        -- repetitive trading USDC/DAI on mainnet
        (
            owner = '\x687f584fd1f4a4d9eb277c03a24fe28f4b0675b7'
            or
            owner = '\x7592b2cccb62c02f0977dd3ad51137888c272bc1'
            or
            owner = '\x278ffae347fa30c4f913d763242908a312485cd5'
        )
        and
        (
            (sell_token = '\xa0b86991c6218b36c1d19d4a2e9eb0ce3606eb48' and buy_token = '\x6b175474e89094c44da98b954eedeac495271d0f')
            or
            (buy_token = '\xa0b86991c6218b36c1d19d4a2e9eb0ce3606eb48' and sell_token = '\x6b175474e89094c44da98b954eedeac495271d0f')
        )
    )
    or
    (
        -- repetitive trading USDC/USDT on mainnet
        (
            owner = '\x9071bfe89d0880edc21e977f3837b5503200f11d'
            or
            owner = '\x4c68eb9fa40716e8ecbe7ca5741cc135ed70f73b'
            or
            owner = '\xebebb015466b4c06bd5b40f3d9bbd3c72d82a529'
            or
            owner = '\x1fe255ad4560784c42d94c3dcf976a0a0d0c589b'
            or
            owner = '\xf6cbda96bff52e2e2f57dc7d12d48fbdf97c495d'
            or
            owner = '\x01d7266d668ab1f53ae50b53f882c74f9fa18499'
            or
            owner = '\x4b526cb21ab23619af2abc8783a5db1813581d87'
            or
            owner = '\xa538a0f53887a220a9b869066c2f2e97eb6dd73b'
            or
            owner = '\x4527ec31207f085ed537bcb0d058756837eabb16'
            or
            owner = '\x687f584fd1f4a4d9eb277c03a24fe28f4b0675b7'
            or
            owner = '\xa9685ca163b19fe5be03fb2aa79fcf04ad3916af'
            or
            owner = '\xc302069440688c8c4108d58ec28a35c44c261528'
        )
        and
        (
            (sell_token = '\xdac17f958d2ee523a2206206994597c13d831ec7' and buy_token = '\xa0b86991c6218b36c1d19d4a2e9eb0ce3606eb48')
            or
            (buy_token = '\xdac17f958d2ee523a2206206994597c13d831ec7' and sell_token = '\xa0b86991c6218b36c1d19d4a2e9eb0ce3606eb48')            
        )
    )
    or
    (
        -- repetitive trading DAI/USDT on mainnet
        owner = '\xbde2ff8a6c87594dff3ef96ef7809be5d5eacde4'
        and
        (
            (sell_token = '\x6b175474e89094c44da98b954eedeac495271d0f' and buy_token = '\xdac17f958d2ee523a2206206994597c13d831ec7')
            or
            (buy_token = '\x6b175474e89094c44da98b954eedeac495271d0f' and sell_token = '\xdac17f958d2ee523a2206206994597c13d831ec7')            
        )
    )
    or
    (
        -- repetitive trading WETH/WSTETH on mainnet
        owner = '\x8ca1187f83f434d5db5c7688fd64bffa281acccc'
        and
        (
            (sell_token = '\x7f39c581f595b53c5cb19bd0b3f8da6c935e2ca0' and buy_token = '\xc02aaa39b223fe8d0a0e5c4f27ead9083c756cc2')
            or
            (buy_token = '\x7f39c581f595b53c5cb19bd0b3f8da6c935e2ca0' and sell_token = '\xc02aaa39b223fe8d0a0e5c4f27ead9083c756cc2')            
        )
    )
    or
    (
        -- repetitive trading USDC/USDBC on Base
        owner = '\xd5c813a01224cabc76e4cd8e10e4029dca0bd7f9'
        and
        (
            (sell_token = '\x833589fcd6edb6e08f4c7c32d4f71b54bda02913' and buy_token = '\xd9aaec86b65d86f6a7b5b1b0c42ffa531710b6ca')
            or
            (buy_token = '\x833589fcd6edb6e08f4c7c32d4f71b54bda02913' and sell_token = '\xd9aaec86b65d86f6a7b5b1b0c42ffa531710b6ca')            
        )
    )
    or
    (
        -- repetitive trading USDC/USDCE on Arbitrum
        owner = '\xd7fcb6fdb9e51507f872442efb4d5c40a60c6d36'
        and
        (
            (sell_token = '\xaf88d065e77c8cc2239327c5edb3a432268e5831' and buy_token = '\xff970a61a04b1ca14834a43f5de4533ebddb5cc8')
            or
            (buy_token = '\xaf88d065e77c8cc2239327c5edb3a432268e5831' and sell_token = '\xff970a61a04b1ca14834a43f5de4533ebddb5cc8')            
        )
    )
    or
    (
        -- repetitive trading WETH/USDC on Base
        owner = '\x2bcd269ff2c06c95834cb3eca0e52987e58cc5b1'
        and
        (
            (sell_token = '\x833589fcd6edb6e08f4c7c32d4f71b54bda02913' and buy_token = '\x4200000000000000000000000000000000000006')
            or
            (buy_token = '\x833589fcd6edb6e08f4c7c32d4f71b54bda02913' and sell_token = '\x4200000000000000000000000000000000000006')            
        )
    )
),
