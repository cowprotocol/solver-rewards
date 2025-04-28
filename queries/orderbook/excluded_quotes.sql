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
            or
            owner = '\xc9821a2e44c9492a50ec7e6381c1a428813f5042'
            or
            owner = '\xe7136a139a73208673fab61963f0e334abcb1ac6'
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
            or
            owner = '\x0f6dd577b7059e5840f8f433fa3cbeedabb2467e'
            or
            owner = '\x787fd1b3c729f386123e2becb829d9bc480eb610'
            or
            owner = '\x4b3bfce15a064acf3178a91fe1e3d0fe579dda52'
            or
            owner = '\x9b31a116e129e36599fdcb08f5e6c208accc4315'
            or
            owner = '\xc9821a2e44c9492a50ec7e6381c1a428813f5042'
            or
            owner = '\x8c4e5102366b8beae2067ab7e6aa8e317f8036e5'
            or
            owner = '\xe7136a139a73208673fab61963f0e334abcb1ac6'
            or
            owner = '\xda0c1131cbfea2194ae5a64c41cb990170094482'
            or
            owner = '\x4b1a6c040fccfc4cd8a85f9305c8da02928f7a93'
            or
            owner = '\xa17bad48903d33b2e598ad2097a3fcd99f86bbb8'
            or
            owner = '\x61d2872d56cd98e9bacc3012644dad911533038f'
            or
            owner = '\x4545d4b5a2a8e8a95d52014efbeab9055d8a2cf2'
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
        (
            owner = '\xbde2ff8a6c87594dff3ef96ef7809be5d5eacde4'
            or
            owner = '\xb497070466dc15fa6420b4781bb0352257146495'
            or
            owner = '\xe7136a139a73208673fab61963f0e334abcb1ac6'
        )
        and
        (
            (sell_token = '\x6b175474e89094c44da98b954eedeac495271d0f' and buy_token = '\xdac17f958d2ee523a2206206994597c13d831ec7')
            or
            (buy_token = '\x6b175474e89094c44da98b954eedeac495271d0f' and sell_token = '\xdac17f958d2ee523a2206206994597c13d831ec7')            
        )
    )
    or
    (
        -- repetitive trading USDS/USDT on mainnet
        owner = '\xc9821a2e44c9492a50ec7e6381c1a428813f5042'
        and
        (
            (sell_token = '\xdc035d45d973e3ec169d2276ddab16f1e407384f' and buy_token = '\xdac17f958d2ee523a2206206994597c13d831ec7')
            or
            (buy_token = '\xdc035d45d973e3ec169d2276ddab16f1e407384f' and sell_token = '\xdac17f958d2ee523a2206206994597c13d831ec7')            
        )
    )
    or
    (
        -- repetitive trading USDS/DAI on mainnet
        owner = '\xc9821a2e44c9492a50ec7e6381c1a428813f5042'
        and
        (
            (sell_token = '\xdc035d45d973e3ec169d2276ddab16f1e407384f' and buy_token = '\x6b175474e89094c44da98b954eedeac495271d0f')
            or
            (buy_token = '\xdc035d45d973e3ec169d2276ddab16f1e407384f' and sell_token = '\x6b175474e89094c44da98b954eedeac495271d0f')            
        )
    )
    or
    (
        -- repetitive trading WETH/WSTETH on mainnet
        (
            owner = '\x8ca1187f83f434d5db5c7688fd64bffa281acccc'
            or
            owner = '\xb4fbdbc8371a1a3ad3b92012c7a3cdad807b6641'
            or
            owner = '\xfd8bc0330655ecf48a3f0695eb07b22416d185f2'
            or
            owner = '\x3bb5c8a00190da68059f0f66c24794584eb10d07'
        )
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
        (
            owner = '\xd5c813a01224cabc76e4cd8e10e4029dca0bd7f9'
            or
            owner = '\x444c4a1add4acdd3fe632b4e7732ac233c1b84aa'
            or
            owner = '\xf15e9c6a2f1c11fbca0db873d0dff310d75917ed'
        )
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
        -- repetitive trading USDC/USDT0 on Arbitrum
        (
            owner = '\x9b31a116e129e36599fdcb08f5e6c208accc4315'
            or
            owner = '\x44c8cf41ec81fbd259abb6b9bb07da43ea55deee'
        )
        and
        (
            (sell_token = '\xfd086bc7cd5c481dcc9c85ebe478a1c0b69fcbb9' and buy_token = '\xaf88d065e77c8cc2239327c5edb3a432268e5831')
            or
            (buy_token = '\xfd086bc7cd5c481dcc9c85ebe478a1c0b69fcbb9' and sell_token = '\xaf88d065e77c8cc2239327c5edb3a432268e5831')
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
    or
    (
        -- repetitive trading USDC/EURe on Gnosis Chain
            owner = '\x52276c1a39c4bcec4f4496388614b0c6214f53d9'
        and
        (
            (sell_token = '\xddafbb505ad214d7b80b1f830fccc89b60fb7a83' and buy_token = '\xcb444e90d8198415266c6a2724b7900fb12fc56e')
            or
            (buy_token = '\xddafbb505ad214d7b80b1f830fccc89b60fb7a83' and sell_token = '\xcb444e90d8198415266c6a2724b7900fb12fc56e')              
        )
    )
    or
    (
        -- repetitive trading USDC/USDCE on Arbitrum
        owner = '\xa465f8761c6a08cc4e60275613833dec23dda7d1'
        and
        (
            (sell_token = '\xaf88d065e77c8cc2239327c5edb3a432268e5831' and buy_token = '\xff970a61a04b1ca14834a43f5de4533ebddb5cc8')
            or
            (buy_token = '\xaf88d065e77c8cc2239327c5edb3a432268e5831' and sell_token = '\xff970a61a04b1ca14834a43f5de4533ebddb5cc8')             
        )
    )
    or
    (
        -- repetitive trading USDC/USDT on Base
        (
            owner = '\x996d749a61c7f56f560f1abe1fc05ed64cc05f75'
            or
            owner = '\x444c4a1add4acdd3fe632b4e7732ac233c1b84aa'
        )
        and
        (
            (sell_token = '\x833589fcd6edb6e08f4c7c32d4f71b54bda02913' and buy_token = '\xfde4c96c8593536e31f229ea8f37b2ada2699bb2')
            or
            (buy_token = '\x833589fcd6edb6e08f4c7c32d4f71b54bda02913' and sell_token = '\xfde4c96c8593536e31f229ea8f37b2ada2699bb2')             
        )
    )
    or
    (
        -- repetitive trading USDC/DAI on Base
        owner = '\x0d19987a99ba9407045f937fc20ff20083662f36'
        and
        (
            (sell_token = '\x833589fcd6edb6e08f4c7c32d4f71b54bda02913' and buy_token = '\x50c5725949a6f0c72e6c4a641f24049a917db0cb')
            or
            (buy_token = '\x833589fcd6edb6e08f4c7c32d4f71b54bda02913' and sell_token = '\x50c5725949a6f0c72e6c4a641f24049a917db0cb')             
        )
    )
    or
    (
        -- repetitive trading USDC/USDS on Base
        owner = '\x444c4a1add4acdd3fe632b4e7732ac233c1b84aa'
        and
        (
            (sell_token = '\x833589fcd6edb6e08f4c7c32d4f71b54bda02913' and buy_token = '\x820c137fa70c8691f0e44dc420a5e53c168921dc')
            or
            (buy_token = '\x833589fcd6edb6e08f4c7c32d4f71b54bda02913' and sell_token = '\x820c137fa70c8691f0e44dc420a5e53c168921dc')             
        )
    )
),
