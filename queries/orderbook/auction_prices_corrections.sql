auction_prices_corrections (blockchain, environment, auction_id, token, price) as ( --noqa: PRS
    select *
    from (
        values 
        -- 0x1c8612facfffd21b56989ada5b740192c70a7f59f6fa257c02ab3cbd2382cef1, protocol fee issue
        ('ethereum', 'prod', 10105330::bigint, '\xad038eb671c44b853887a7e32528fab35dc5d710'::bytea, 43314929461672::numeric(78, 0)),

        -- 0x4d4a1218787a5d3e87f63774d7422771537a846e9a55d3447c56f14b399ddf3c, protocol fee issue
        ('ethereum', 'prod', 10105327::bigint, '\x06b964d96f5dcf7eae9d7c559b09edce244d4b8e'::bytea, 124975619281188::numeric(78, 0)),

        -- 0xc6b996f74c9c6df1d79806e88fb6a6f17ea11eef521644ec6fecc8fdf5d8d571, network fee issue
        ('ethereum', 'prod', 10105270::bigint, '\x4c5cb5d87709387f8821709f7a6664f00dcf0c93'::bytea, 3464500573709::numeric(78, 0)),

        -- 0x9cf5a2a1cea3548c934b13610e83f79ee94f8a6974082b1ebebbbd03c3d1b887, network fee issue
        ('ethereum', 'prod', 10105162::bigint, '\xe2cfd7a01ec63875cd9da6c7c1b7025166c2fa2f'::bytea, 163508274::numeric(78, 0)),

        -- 0x72e083668ae99eb9ae0b936e1e132c302b088ce8f49f36130b4b472d98d8abce, network fee issue
        ('ethereum', 'prod', 10105159::bigint, '\xe2cfd7a01ec63875cd9da6c7c1b7025166c2fa2f'::bytea, 163508274::numeric(78, 0)),

        -- 0x15c54ff228b4ab388c2597a80d43c672b2ef659e8b2fb296e447d63281ad305f, protocol fee issue
        ('ethereum', 'prod', 10105158::bigint, '\x06b964d96f5dcf7eae9d7c559b09edce244d4b8e'::bytea, 124975619281188::numeric(78, 0)),

        -- 0xdd94895f5c298ae61ca14c15c0e99b361d96bc3c667dd155eec1ea59bb99845d, network fee issue
        ('ethereum', 'prod', 10105154::bigint, '\xe2cfd7a01ec63875cd9da6c7c1b7025166c2fa2f'::bytea, 163508274::numeric(78, 0)),

        -- 0xda1cbce2d955bb2f072635be29ef4f14660493b9b5d344f2e911d2f6927eb64c, network fee issue
        ('ethereum', 'prod', 10105150::bigint, '\xe2cfd7a01ec63875cd9da6c7c1b7025166c2fa2f'::bytea, 163508274::numeric(78, 0)),

        -- 0x113173806a780ada8164edcd8accfc29196ff67909c11807e7b98933c2d058da, network fee issue
        ('ethereum', 'prod', 10105145::bigint, '\x66b5228cfd34d9f4d9f03188d67816286c7c0b74'::bytea, 859279431572::numeric(78, 0)),

        -- 0xcd56ad32fa719a00fc44b7d0934e3316d1106142911eec0b3b41dd34f4354f96, protocol fee issue
        ('ethereum', 'prod', 10105124::bigint, '\x5c47902c8c80779cb99235e42c354e53f38c3b0d'::bytea, 101902651::numeric(78, 0)),

        -- 0x1b1dfef2b14e6d9905acc2131817d8d9f58bcdfc425cbb370b0360e597dc0bf1, network fee issue
        ('ethereum', 'prod', 10105008::bigint, '\xe2cfd7a01ec63875cd9da6c7c1b7025166c2fa2f'::bytea, 163508274::numeric(78, 0)),

        -- 0x48a58a8e5eb3ed4dd0c637338753ae62076a67ddf51b1c0ede701935dc08b66b, network fee issue
        ('ethereum', 'prod', 10104988::bigint, '\xe2cfd7a01ec63875cd9da6c7c1b7025166c2fa2f'::bytea, 163508274::numeric(78, 0)),

        -- 0x8860e2b131547119566d2cd75acb5643a922fbfc68dfba1176bf608b0ce8ea01, network fee issue
        ('ethereum', 'prod', 10104987::bigint, '\xe2cfd7a01ec63875cd9da6c7c1b7025166c2fa2f'::bytea, 163508274::numeric(78, 0)),

        -- 0xafc84eea4320e91c0e5eb7c1d1a24e03b2b764d1d9c7d6f97df42efab4a3bd62, network fee issue
        ('ethereum', 'prod', 10104982::bigint, '\xe2cfd7a01ec63875cd9da6c7c1b7025166c2fa2f'::bytea, 163508274::numeric(78, 0)),

        -- 0x8aa4e5977d604abc9183036d21a2cdb17f66e490474cec6e6d069d0cb858d25d, protocol fee issue
        ('ethereum', 'prod', 10104824::bigint, '\x0943d06a5ff3b25ddc51642717680c105ad63c01'::bytea, 144858293311::numeric(78, 0)),

        -- 0xa743eef8e27e85f02e75778de908be0bd5416678be2bd29bf8d984a37b4e7bd2, network fee issue
        ('ethereum', 'prod', 10104816::bigint, '\x777172d858dc1599914a1c4c6c9fc48c99a60990'::bytea, 37515633095045::numeric(78, 0)),

        -- 0x4fc54d82ab8b1488dbe6a65cb0fe79511aa93fd0748a8a1eed3dd0979f4c8920, network fee issue
        ('ethereum', 'prod', 10104812::bigint, '\x777172d858dc1599914a1c4c6c9fc48c99a60990'::bytea, 37515633095045::numeric(78, 0)),

        -- 0x8e1a1801f21b2f1972480aa8c3f72dc0b99228b71281d1401357c252b0485b76, network fee issue
        ('ethereum', 'prod', 10104810::bigint, '\x777172d858dc1599914a1c4c6c9fc48c99a60990'::bytea, 37515633095045::numeric(78, 0)),

        -- 0xa8effb0d951d650353dba5409e25e4affa141d62f91d523e21247a2f4153413e, network fee issue
        ('ethereum', 'prod', 10104808::bigint, '\x777172d858dc1599914a1c4c6c9fc48c99a60990'::bytea, 37515633095045::numeric(78, 0)),

        -- 0x04d6c08273e587f7ccca09100d8a432ecef87444e9e7a6ae17a1f2f36bedb1eb, network fee issue
        ('ethereum', 'prod', 10104805::bigint, '\x777172d858dc1599914a1c4c6c9fc48c99a60990'::bytea, 37515633095045::numeric(78, 0)),

        -- 0x04d6c08273e587f7ccca09100d8a432ecef87444e9e7a6ae17a1f2f36bedb1eb, network fee issue
        ('ethereum', 'prod', 10104805::bigint, '\x9f278dc799bbc61ecb8e5fb8035cbfa29803623b'::bytea, 1274000005::numeric(78, 0)),

        -- 0xbbeb89e06b30614b6364c362bae217b541e7b9c72dc4fe9d0c93622fed028f91, network fee issue
        ('ethereum', 'prod', 10104748::bigint, '\x4eca7761a516f8300711cbf920c0b85555261993'::bytea, 23670618::numeric(78, 0)),

        -- 0x958089dd2a50f555f89f872c9fb83882d29750f78ad3096c9f535b08e030928e, network fee issue
        ('ethereum', 'prod', 10104733::bigint, '\xad038eb671c44b853887a7e32528fab35dc5d710'::bytea, 43314929461672::numeric(78, 0)),

        -- 0xb46617d67c592518ed51d2a00292d0e86728b1ac9aa700220c0b010b19b5f96b, network fee issue
        ('ethereum', 'prod', 10104715::bigint, '\x1a88df1cfe15af22b3c4c783d4e6f7f9e0c1885d'::bytea, 318978711000518::numeric(78, 0)),

        -- 0xd6bd149df0d16cc26b1e2581e25340bf6aa31bf218cbffd4cbb5e55e9d1dfae2, network fee issue
        ('ethereum', 'prod', 10104624::bigint, '\x4eca7761a516f8300711cbf920c0b85555261993'::bytea, 23670618::numeric(78, 0)),

        -- https://etherscan.io/tx/0x130ec24cc595a803431e78aaf4013168f82cc61a626fcbb3d73e6dae62350ba7, protocol fee issue
        -- price taken from nearby auction 10325156
        ('ethereum', 'prod', 10325171::bigint, '\x35d8949372d46b7a3d5a56006ae77b215fc69bc0'::bytea, 533247805376780::numeric(78, 0)),

        -- correction only relevant for the tests in the test_batch_rewards.py file
        ('ethereum', 'prod', 53::bigint, '\x02'::bytea, 500000000000000::numeric(78, 0))

    ) as temp(blockchain, environment, auction_id, token, price)
    where blockchain = '{{blockchain}}' and environment = '{{environment}}'
),
