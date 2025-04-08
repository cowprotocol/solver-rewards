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

        -- bogus baseline price for USDC that caused a crazy native price for the token
        -- query to confirm results: select * from auction_prices where token='\xa0b86991c6218b36c1d19d4a2e9eb0ce3606eb48' and price > 56150942718177291268870111000;
        -- fixing 29 auctions in total

        ('ethereum', 'prod', 10410755::bigint, '\xa0b86991c6218b36c1d19d4a2e9eb0ce3606eb48'::bytea, 524485367578693373855268864::numeric(78, 0)),
        ('ethereum', 'prod', 10410754::bigint, '\xa0b86991c6218b36c1d19d4a2e9eb0ce3606eb48'::bytea, 524485367578693373855268864::numeric(78, 0)),
        ('ethereum', 'prod', 10410753::bigint, '\xa0b86991c6218b36c1d19d4a2e9eb0ce3606eb48'::bytea, 524485367578693373855268864::numeric(78, 0)),
        ('ethereum', 'prod', 10410752::bigint, '\xa0b86991c6218b36c1d19d4a2e9eb0ce3606eb48'::bytea, 524485367578693373855268864::numeric(78, 0)),
        ('ethereum', 'prod', 10410751::bigint, '\xa0b86991c6218b36c1d19d4a2e9eb0ce3606eb48'::bytea, 524485367578693373855268864::numeric(78, 0)),
        ('ethereum', 'prod', 10410750::bigint, '\xa0b86991c6218b36c1d19d4a2e9eb0ce3606eb48'::bytea, 524485367578693373855268864::numeric(78, 0)),
        ('ethereum', 'prod', 10410749::bigint, '\xa0b86991c6218b36c1d19d4a2e9eb0ce3606eb48'::bytea, 524485367578693373855268864::numeric(78, 0)),
        ('ethereum', 'prod', 10410748::bigint, '\xa0b86991c6218b36c1d19d4a2e9eb0ce3606eb48'::bytea, 524485367578693373855268864::numeric(78, 0)),
        ('ethereum', 'prod', 10410747::bigint, '\xa0b86991c6218b36c1d19d4a2e9eb0ce3606eb48'::bytea, 524485367578693373855268864::numeric(78, 0)),
        ('ethereum', 'prod', 10410746::bigint, '\xa0b86991c6218b36c1d19d4a2e9eb0ce3606eb48'::bytea, 524485367578693373855268864::numeric(78, 0)),
        ('ethereum', 'prod', 10410745::bigint, '\xa0b86991c6218b36c1d19d4a2e9eb0ce3606eb48'::bytea, 524485367578693373855268864::numeric(78, 0)),
        ('ethereum', 'prod', 10410744::bigint, '\xa0b86991c6218b36c1d19d4a2e9eb0ce3606eb48'::bytea, 524485367578693373855268864::numeric(78, 0)),
        ('ethereum', 'prod', 10410743::bigint, '\xa0b86991c6218b36c1d19d4a2e9eb0ce3606eb48'::bytea, 524485367578693373855268864::numeric(78, 0)),
        ('ethereum', 'prod', 10410742::bigint, '\xa0b86991c6218b36c1d19d4a2e9eb0ce3606eb48'::bytea, 524485367578693373855268864::numeric(78, 0)),
        ('ethereum', 'prod', 10410741::bigint, '\xa0b86991c6218b36c1d19d4a2e9eb0ce3606eb48'::bytea, 524485367578693373855268864::numeric(78, 0)),
        ('ethereum', 'prod', 10410740::bigint, '\xa0b86991c6218b36c1d19d4a2e9eb0ce3606eb48'::bytea, 524485367578693373855268864::numeric(78, 0)),
        ('ethereum', 'prod', 10410739::bigint, '\xa0b86991c6218b36c1d19d4a2e9eb0ce3606eb48'::bytea, 524485367578693373855268864::numeric(78, 0)),
        ('ethereum', 'prod', 10410738::bigint, '\xa0b86991c6218b36c1d19d4a2e9eb0ce3606eb48'::bytea, 524485367578693373855268864::numeric(78, 0)),
        ('ethereum', 'prod', 10410737::bigint, '\xa0b86991c6218b36c1d19d4a2e9eb0ce3606eb48'::bytea, 524485367578693373855268864::numeric(78, 0)),
        ('ethereum', 'prod', 10410736::bigint, '\xa0b86991c6218b36c1d19d4a2e9eb0ce3606eb48'::bytea, 524485367578693373855268864::numeric(78, 0)),
        ('ethereum', 'prod', 10410735::bigint, '\xa0b86991c6218b36c1d19d4a2e9eb0ce3606eb48'::bytea, 524485367578693373855268864::numeric(78, 0)),
        ('ethereum', 'prod', 10410734::bigint, '\xa0b86991c6218b36c1d19d4a2e9eb0ce3606eb48'::bytea, 524485367578693373855268864::numeric(78, 0)),
        ('ethereum', 'prod', 10410733::bigint, '\xa0b86991c6218b36c1d19d4a2e9eb0ce3606eb48'::bytea, 524485367578693373855268864::numeric(78, 0)),
        ('ethereum', 'prod', 10410732::bigint, '\xa0b86991c6218b36c1d19d4a2e9eb0ce3606eb48'::bytea, 524485367578693373855268864::numeric(78, 0)),
        ('ethereum', 'prod', 10410731::bigint, '\xa0b86991c6218b36c1d19d4a2e9eb0ce3606eb48'::bytea, 524485367578693373855268864::numeric(78, 0)),
        ('ethereum', 'prod', 10410730::bigint, '\xa0b86991c6218b36c1d19d4a2e9eb0ce3606eb48'::bytea, 524485367578693373855268864::numeric(78, 0)),
        ('ethereum', 'prod', 10410729::bigint, '\xa0b86991c6218b36c1d19d4a2e9eb0ce3606eb48'::bytea, 524485367578693373855268864::numeric(78, 0)),
        ('ethereum', 'prod', 10410728::bigint, '\xa0b86991c6218b36c1d19d4a2e9eb0ce3606eb48'::bytea, 524485367578693373855268864::numeric(78, 0)),
        ('ethereum', 'prod', 10410727::bigint, '\xa0b86991c6218b36c1d19d4a2e9eb0ce3606eb48'::bytea, 524485367578693373855268864::numeric(78, 0)),

        ----------- USDC fix done -----------

        -- bogus native price for USD0++
        -- query to confirm results: 
        -- select * from auction_prices
        -- where token='\x35d8949372d46b7a3d5a56006ae77b215fc69bc0'
        -- and price >= 800706958144168 and auction_id > 10448500;
        -- fixing 208 auctions in total 

        ('ethereum', 'prod', 10448631::bigint, '\x35d8949372d46b7a3d5a56006ae77b215fc69bc0', 518764441006038::numeric(78, 0)),
        ('ethereum', 'prod', 10448632::bigint, '\x35d8949372d46b7a3d5a56006ae77b215fc69bc0', 518764441006038::numeric(78, 0)),
        ('ethereum', 'prod', 10448633::bigint, '\x35d8949372d46b7a3d5a56006ae77b215fc69bc0', 518764441006038::numeric(78, 0)),
        ('ethereum', 'prod', 10448634::bigint, '\x35d8949372d46b7a3d5a56006ae77b215fc69bc0', 518764441006038::numeric(78, 0)),
        ('ethereum', 'prod', 10448635::bigint, '\x35d8949372d46b7a3d5a56006ae77b215fc69bc0', 518764441006038::numeric(78, 0)),
        ('ethereum', 'prod', 10448636::bigint, '\x35d8949372d46b7a3d5a56006ae77b215fc69bc0', 518764441006038::numeric(78, 0)),
        ('ethereum', 'prod', 10448637::bigint, '\x35d8949372d46b7a3d5a56006ae77b215fc69bc0', 518764441006038::numeric(78, 0)),
        ('ethereum', 'prod', 10448638::bigint, '\x35d8949372d46b7a3d5a56006ae77b215fc69bc0', 518764441006038::numeric(78, 0)),
        ('ethereum', 'prod', 10448639::bigint, '\x35d8949372d46b7a3d5a56006ae77b215fc69bc0', 518764441006038::numeric(78, 0)),
        ('ethereum', 'prod', 10448640::bigint, '\x35d8949372d46b7a3d5a56006ae77b215fc69bc0', 518764441006038::numeric(78, 0)),
        ('ethereum', 'prod', 10448641::bigint, '\x35d8949372d46b7a3d5a56006ae77b215fc69bc0', 518764441006038::numeric(78, 0)),
        ('ethereum', 'prod', 10448642::bigint, '\x35d8949372d46b7a3d5a56006ae77b215fc69bc0', 518764441006038::numeric(78, 0)),
        ('ethereum', 'prod', 10448643::bigint, '\x35d8949372d46b7a3d5a56006ae77b215fc69bc0', 518764441006038::numeric(78, 0)),
        ('ethereum', 'prod', 10448644::bigint, '\x35d8949372d46b7a3d5a56006ae77b215fc69bc0', 518764441006038::numeric(78, 0)),
        ('ethereum', 'prod', 10448645::bigint, '\x35d8949372d46b7a3d5a56006ae77b215fc69bc0', 518764441006038::numeric(78, 0)),
        ('ethereum', 'prod', 10448646::bigint, '\x35d8949372d46b7a3d5a56006ae77b215fc69bc0', 518764441006038::numeric(78, 0)),
        ('ethereum', 'prod', 10448648::bigint, '\x35d8949372d46b7a3d5a56006ae77b215fc69bc0', 518764441006038::numeric(78, 0)),
        ('ethereum', 'prod', 10448649::bigint, '\x35d8949372d46b7a3d5a56006ae77b215fc69bc0', 518764441006038::numeric(78, 0)),
        ('ethereum', 'prod', 10448650::bigint, '\x35d8949372d46b7a3d5a56006ae77b215fc69bc0', 518764441006038::numeric(78, 0)),
        ('ethereum', 'prod', 10448652::bigint, '\x35d8949372d46b7a3d5a56006ae77b215fc69bc0', 518764441006038::numeric(78, 0)),
        ('ethereum', 'prod', 10448658::bigint, '\x35d8949372d46b7a3d5a56006ae77b215fc69bc0', 518764441006038::numeric(78, 0)),
        ('ethereum', 'prod', 10448659::bigint, '\x35d8949372d46b7a3d5a56006ae77b215fc69bc0', 518764441006038::numeric(78, 0)),
        ('ethereum', 'prod', 10448660::bigint, '\x35d8949372d46b7a3d5a56006ae77b215fc69bc0', 518764441006038::numeric(78, 0)),
        ('ethereum', 'prod', 10448661::bigint, '\x35d8949372d46b7a3d5a56006ae77b215fc69bc0', 518764441006038::numeric(78, 0)),
        ('ethereum', 'prod', 10448901::bigint, '\x35d8949372d46b7a3d5a56006ae77b215fc69bc0', 518764441006038::numeric(78, 0)),
        ('ethereum', 'prod', 10448902::bigint, '\x35d8949372d46b7a3d5a56006ae77b215fc69bc0', 518764441006038::numeric(78, 0)),
        ('ethereum', 'prod', 10448903::bigint, '\x35d8949372d46b7a3d5a56006ae77b215fc69bc0', 518764441006038::numeric(78, 0)),
        ('ethereum', 'prod', 10448904::bigint, '\x35d8949372d46b7a3d5a56006ae77b215fc69bc0', 518764441006038::numeric(78, 0)),
        ('ethereum', 'prod', 10448905::bigint, '\x35d8949372d46b7a3d5a56006ae77b215fc69bc0', 518764441006038::numeric(78, 0)),
        ('ethereum', 'prod', 10448906::bigint, '\x35d8949372d46b7a3d5a56006ae77b215fc69bc0', 518764441006038::numeric(78, 0)),
        ('ethereum', 'prod', 10448907::bigint, '\x35d8949372d46b7a3d5a56006ae77b215fc69bc0', 518764441006038::numeric(78, 0)),
        ('ethereum', 'prod', 10448908::bigint, '\x35d8949372d46b7a3d5a56006ae77b215fc69bc0', 518764441006038::numeric(78, 0)),
        ('ethereum', 'prod', 10448909::bigint, '\x35d8949372d46b7a3d5a56006ae77b215fc69bc0', 518764441006038::numeric(78, 0)),
        ('ethereum', 'prod', 10448910::bigint, '\x35d8949372d46b7a3d5a56006ae77b215fc69bc0', 518764441006038::numeric(78, 0)),
        ('ethereum', 'prod', 10448912::bigint, '\x35d8949372d46b7a3d5a56006ae77b215fc69bc0', 518764441006038::numeric(78, 0)),
        ('ethereum', 'prod', 10448913::bigint, '\x35d8949372d46b7a3d5a56006ae77b215fc69bc0', 518764441006038::numeric(78, 0)),
        ('ethereum', 'prod', 10448919::bigint, '\x35d8949372d46b7a3d5a56006ae77b215fc69bc0', 518764441006038::numeric(78, 0)),
        ('ethereum', 'prod', 10448920::bigint, '\x35d8949372d46b7a3d5a56006ae77b215fc69bc0', 518764441006038::numeric(78, 0)),
        ('ethereum', 'prod', 10448922::bigint, '\x35d8949372d46b7a3d5a56006ae77b215fc69bc0', 518764441006038::numeric(78, 0)),
        ('ethereum', 'prod', 10448925::bigint, '\x35d8949372d46b7a3d5a56006ae77b215fc69bc0', 518764441006038::numeric(78, 0)),
        ('ethereum', 'prod', 10448926::bigint, '\x35d8949372d46b7a3d5a56006ae77b215fc69bc0', 518764441006038::numeric(78, 0)),
        ('ethereum', 'prod', 10448928::bigint, '\x35d8949372d46b7a3d5a56006ae77b215fc69bc0', 518764441006038::numeric(78, 0)),
        ('ethereum', 'prod', 10448929::bigint, '\x35d8949372d46b7a3d5a56006ae77b215fc69bc0', 518764441006038::numeric(78, 0)),
        ('ethereum', 'prod', 10448931::bigint, '\x35d8949372d46b7a3d5a56006ae77b215fc69bc0', 518764441006038::numeric(78, 0)),
        ('ethereum', 'prod', 10448932::bigint, '\x35d8949372d46b7a3d5a56006ae77b215fc69bc0', 518764441006038::numeric(78, 0)),
        ('ethereum', 'prod', 10448935::bigint, '\x35d8949372d46b7a3d5a56006ae77b215fc69bc0', 518764441006038::numeric(78, 0)),
        ('ethereum', 'prod', 10448939::bigint, '\x35d8949372d46b7a3d5a56006ae77b215fc69bc0', 518764441006038::numeric(78, 0)),
        ('ethereum', 'prod', 10448940::bigint, '\x35d8949372d46b7a3d5a56006ae77b215fc69bc0', 518764441006038::numeric(78, 0)),
        ('ethereum', 'prod', 10448945::bigint, '\x35d8949372d46b7a3d5a56006ae77b215fc69bc0', 518764441006038::numeric(78, 0)),
        ('ethereum', 'prod', 10448947::bigint, '\x35d8949372d46b7a3d5a56006ae77b215fc69bc0', 518764441006038::numeric(78, 0)),
        ('ethereum', 'prod', 10448948::bigint, '\x35d8949372d46b7a3d5a56006ae77b215fc69bc0', 518764441006038::numeric(78, 0)),
        ('ethereum', 'prod', 10448949::bigint, '\x35d8949372d46b7a3d5a56006ae77b215fc69bc0', 518764441006038::numeric(78, 0)),
        ('ethereum', 'prod', 10448950::bigint, '\x35d8949372d46b7a3d5a56006ae77b215fc69bc0', 518764441006038::numeric(78, 0)),
        ('ethereum', 'prod', 10448952::bigint, '\x35d8949372d46b7a3d5a56006ae77b215fc69bc0', 518764441006038::numeric(78, 0)),
        ('ethereum', 'prod', 10448953::bigint, '\x35d8949372d46b7a3d5a56006ae77b215fc69bc0', 518764441006038::numeric(78, 0)),
        ('ethereum', 'prod', 10448954::bigint, '\x35d8949372d46b7a3d5a56006ae77b215fc69bc0', 518764441006038::numeric(78, 0)),
        ('ethereum', 'prod', 10448957::bigint, '\x35d8949372d46b7a3d5a56006ae77b215fc69bc0', 518764441006038::numeric(78, 0)),
        ('ethereum', 'prod', 10448958::bigint, '\x35d8949372d46b7a3d5a56006ae77b215fc69bc0', 518764441006038::numeric(78, 0)),
        ('ethereum', 'prod', 10448959::bigint, '\x35d8949372d46b7a3d5a56006ae77b215fc69bc0', 518764441006038::numeric(78, 0)),
        ('ethereum', 'prod', 10448960::bigint, '\x35d8949372d46b7a3d5a56006ae77b215fc69bc0', 518764441006038::numeric(78, 0)),
        ('ethereum', 'prod', 10448961::bigint, '\x35d8949372d46b7a3d5a56006ae77b215fc69bc0', 518764441006038::numeric(78, 0)),
        ('ethereum', 'prod', 10448962::bigint, '\x35d8949372d46b7a3d5a56006ae77b215fc69bc0', 518764441006038::numeric(78, 0)),
        ('ethereum', 'prod', 10448963::bigint, '\x35d8949372d46b7a3d5a56006ae77b215fc69bc0', 518764441006038::numeric(78, 0)),
        ('ethereum', 'prod', 10448964::bigint, '\x35d8949372d46b7a3d5a56006ae77b215fc69bc0', 518764441006038::numeric(78, 0)),
        ('ethereum', 'prod', 10448965::bigint, '\x35d8949372d46b7a3d5a56006ae77b215fc69bc0', 518764441006038::numeric(78, 0)),
        ('ethereum', 'prod', 10448966::bigint, '\x35d8949372d46b7a3d5a56006ae77b215fc69bc0', 518764441006038::numeric(78, 0)),
        ('ethereum', 'prod', 10448967::bigint, '\x35d8949372d46b7a3d5a56006ae77b215fc69bc0', 518764441006038::numeric(78, 0)),
        ('ethereum', 'prod', 10448968::bigint, '\x35d8949372d46b7a3d5a56006ae77b215fc69bc0', 518764441006038::numeric(78, 0)),
        ('ethereum', 'prod', 10448969::bigint, '\x35d8949372d46b7a3d5a56006ae77b215fc69bc0', 518764441006038::numeric(78, 0)),
        ('ethereum', 'prod', 10448970::bigint, '\x35d8949372d46b7a3d5a56006ae77b215fc69bc0', 518764441006038::numeric(78, 0)),
        ('ethereum', 'prod', 10448972::bigint, '\x35d8949372d46b7a3d5a56006ae77b215fc69bc0', 518764441006038::numeric(78, 0)),
        ('ethereum', 'prod', 10448973::bigint, '\x35d8949372d46b7a3d5a56006ae77b215fc69bc0', 518764441006038::numeric(78, 0)),
        ('ethereum', 'prod', 10448974::bigint, '\x35d8949372d46b7a3d5a56006ae77b215fc69bc0', 518764441006038::numeric(78, 0)),
        ('ethereum', 'prod', 10448975::bigint, '\x35d8949372d46b7a3d5a56006ae77b215fc69bc0', 518764441006038::numeric(78, 0)),
        ('ethereum', 'prod', 10448976::bigint, '\x35d8949372d46b7a3d5a56006ae77b215fc69bc0', 518764441006038::numeric(78, 0)),
        ('ethereum', 'prod', 10448977::bigint, '\x35d8949372d46b7a3d5a56006ae77b215fc69bc0', 518764441006038::numeric(78, 0)),
        ('ethereum', 'prod', 10448978::bigint, '\x35d8949372d46b7a3d5a56006ae77b215fc69bc0', 518764441006038::numeric(78, 0)),
        ('ethereum', 'prod', 10448979::bigint, '\x35d8949372d46b7a3d5a56006ae77b215fc69bc0', 518764441006038::numeric(78, 0)),
        ('ethereum', 'prod', 10448980::bigint, '\x35d8949372d46b7a3d5a56006ae77b215fc69bc0', 518764441006038::numeric(78, 0)),
        ('ethereum', 'prod', 10448981::bigint, '\x35d8949372d46b7a3d5a56006ae77b215fc69bc0', 518764441006038::numeric(78, 0)),
        ('ethereum', 'prod', 10448982::bigint, '\x35d8949372d46b7a3d5a56006ae77b215fc69bc0', 518764441006038::numeric(78, 0)),
        ('ethereum', 'prod', 10448983::bigint, '\x35d8949372d46b7a3d5a56006ae77b215fc69bc0', 518764441006038::numeric(78, 0)),
        ('ethereum', 'prod', 10448984::bigint, '\x35d8949372d46b7a3d5a56006ae77b215fc69bc0', 518764441006038::numeric(78, 0)),
        ('ethereum', 'prod', 10448985::bigint, '\x35d8949372d46b7a3d5a56006ae77b215fc69bc0', 518764441006038::numeric(78, 0)),
        ('ethereum', 'prod', 10448986::bigint, '\x35d8949372d46b7a3d5a56006ae77b215fc69bc0', 518764441006038::numeric(78, 0)),
        ('ethereum', 'prod', 10448987::bigint, '\x35d8949372d46b7a3d5a56006ae77b215fc69bc0', 518764441006038::numeric(78, 0)),
        ('ethereum', 'prod', 10448988::bigint, '\x35d8949372d46b7a3d5a56006ae77b215fc69bc0', 518764441006038::numeric(78, 0)),
        ('ethereum', 'prod', 10448989::bigint, '\x35d8949372d46b7a3d5a56006ae77b215fc69bc0', 518764441006038::numeric(78, 0)),
        ('ethereum', 'prod', 10448990::bigint, '\x35d8949372d46b7a3d5a56006ae77b215fc69bc0', 518764441006038::numeric(78, 0)),
        ('ethereum', 'prod', 10448991::bigint, '\x35d8949372d46b7a3d5a56006ae77b215fc69bc0', 518764441006038::numeric(78, 0)),
        ('ethereum', 'prod', 10448992::bigint, '\x35d8949372d46b7a3d5a56006ae77b215fc69bc0', 518764441006038::numeric(78, 0)),
        ('ethereum', 'prod', 10448993::bigint, '\x35d8949372d46b7a3d5a56006ae77b215fc69bc0', 518764441006038::numeric(78, 0)),
        ('ethereum', 'prod', 10448995::bigint, '\x35d8949372d46b7a3d5a56006ae77b215fc69bc0', 518764441006038::numeric(78, 0)),
        ('ethereum', 'prod', 10448997::bigint, '\x35d8949372d46b7a3d5a56006ae77b215fc69bc0', 518764441006038::numeric(78, 0)),
        ('ethereum', 'prod', 10448998::bigint, '\x35d8949372d46b7a3d5a56006ae77b215fc69bc0', 518764441006038::numeric(78, 0)),
        ('ethereum', 'prod', 10448999::bigint, '\x35d8949372d46b7a3d5a56006ae77b215fc69bc0', 518764441006038::numeric(78, 0)),
        ('ethereum', 'prod', 10449000::bigint, '\x35d8949372d46b7a3d5a56006ae77b215fc69bc0', 518764441006038::numeric(78, 0)),
        ('ethereum', 'prod', 10449001::bigint, '\x35d8949372d46b7a3d5a56006ae77b215fc69bc0', 518764441006038::numeric(78, 0)),
        ('ethereum', 'prod', 10449003::bigint, '\x35d8949372d46b7a3d5a56006ae77b215fc69bc0', 518764441006038::numeric(78, 0)),
        ('ethereum', 'prod', 10449004::bigint, '\x35d8949372d46b7a3d5a56006ae77b215fc69bc0', 518764441006038::numeric(78, 0)),
        ('ethereum', 'prod', 10449006::bigint, '\x35d8949372d46b7a3d5a56006ae77b215fc69bc0', 518764441006038::numeric(78, 0)),
        ('ethereum', 'prod', 10449007::bigint, '\x35d8949372d46b7a3d5a56006ae77b215fc69bc0', 518764441006038::numeric(78, 0)),
        ('ethereum', 'prod', 10449008::bigint, '\x35d8949372d46b7a3d5a56006ae77b215fc69bc0', 518764441006038::numeric(78, 0)),
        ('ethereum', 'prod', 10449009::bigint, '\x35d8949372d46b7a3d5a56006ae77b215fc69bc0', 518764441006038::numeric(78, 0)),
        ('ethereum', 'prod', 10449011::bigint, '\x35d8949372d46b7a3d5a56006ae77b215fc69bc0', 518764441006038::numeric(78, 0)),
        ('ethereum', 'prod', 10449012::bigint, '\x35d8949372d46b7a3d5a56006ae77b215fc69bc0', 518764441006038::numeric(78, 0)),
        ('ethereum', 'prod', 10449013::bigint, '\x35d8949372d46b7a3d5a56006ae77b215fc69bc0', 518764441006038::numeric(78, 0)),
        ('ethereum', 'prod', 10449014::bigint, '\x35d8949372d46b7a3d5a56006ae77b215fc69bc0', 518764441006038::numeric(78, 0)),
        ('ethereum', 'prod', 10449015::bigint, '\x35d8949372d46b7a3d5a56006ae77b215fc69bc0', 518764441006038::numeric(78, 0)),
        ('ethereum', 'prod', 10449016::bigint, '\x35d8949372d46b7a3d5a56006ae77b215fc69bc0', 518764441006038::numeric(78, 0)),
        ('ethereum', 'prod', 10449017::bigint, '\x35d8949372d46b7a3d5a56006ae77b215fc69bc0', 518764441006038::numeric(78, 0)),
        ('ethereum', 'prod', 10449018::bigint, '\x35d8949372d46b7a3d5a56006ae77b215fc69bc0', 518764441006038::numeric(78, 0)),
        ('ethereum', 'prod', 10449019::bigint, '\x35d8949372d46b7a3d5a56006ae77b215fc69bc0', 518764441006038::numeric(78, 0)),
        ('ethereum', 'prod', 10449021::bigint, '\x35d8949372d46b7a3d5a56006ae77b215fc69bc0', 518764441006038::numeric(78, 0)),
        ('ethereum', 'prod', 10449022::bigint, '\x35d8949372d46b7a3d5a56006ae77b215fc69bc0', 518764441006038::numeric(78, 0)),
        ('ethereum', 'prod', 10449024::bigint, '\x35d8949372d46b7a3d5a56006ae77b215fc69bc0', 518764441006038::numeric(78, 0)),
        ('ethereum', 'prod', 10449025::bigint, '\x35d8949372d46b7a3d5a56006ae77b215fc69bc0', 518764441006038::numeric(78, 0)),
        ('ethereum', 'prod', 10449026::bigint, '\x35d8949372d46b7a3d5a56006ae77b215fc69bc0', 518764441006038::numeric(78, 0)),
        ('ethereum', 'prod', 10449031::bigint, '\x35d8949372d46b7a3d5a56006ae77b215fc69bc0', 518764441006038::numeric(78, 0)),
        ('ethereum', 'prod', 10449032::bigint, '\x35d8949372d46b7a3d5a56006ae77b215fc69bc0', 518764441006038::numeric(78, 0)),
        ('ethereum', 'prod', 10449033::bigint, '\x35d8949372d46b7a3d5a56006ae77b215fc69bc0', 518764441006038::numeric(78, 0)),
        ('ethereum', 'prod', 10449034::bigint, '\x35d8949372d46b7a3d5a56006ae77b215fc69bc0', 518764441006038::numeric(78, 0)),
        ('ethereum', 'prod', 10449035::bigint, '\x35d8949372d46b7a3d5a56006ae77b215fc69bc0', 518764441006038::numeric(78, 0)),
        ('ethereum', 'prod', 10449036::bigint, '\x35d8949372d46b7a3d5a56006ae77b215fc69bc0', 518764441006038::numeric(78, 0)),
        ('ethereum', 'prod', 10449037::bigint, '\x35d8949372d46b7a3d5a56006ae77b215fc69bc0', 518764441006038::numeric(78, 0)),
        ('ethereum', 'prod', 10449038::bigint, '\x35d8949372d46b7a3d5a56006ae77b215fc69bc0', 518764441006038::numeric(78, 0)),
        ('ethereum', 'prod', 10449039::bigint, '\x35d8949372d46b7a3d5a56006ae77b215fc69bc0', 518764441006038::numeric(78, 0)),
        ('ethereum', 'prod', 10449040::bigint, '\x35d8949372d46b7a3d5a56006ae77b215fc69bc0', 518764441006038::numeric(78, 0)),
        ('ethereum', 'prod', 10449041::bigint, '\x35d8949372d46b7a3d5a56006ae77b215fc69bc0', 518764441006038::numeric(78, 0)),
        ('ethereum', 'prod', 10449042::bigint, '\x35d8949372d46b7a3d5a56006ae77b215fc69bc0', 518764441006038::numeric(78, 0)),
        ('ethereum', 'prod', 10449047::bigint, '\x35d8949372d46b7a3d5a56006ae77b215fc69bc0', 518764441006038::numeric(78, 0)),
        ('ethereum', 'prod', 10449049::bigint, '\x35d8949372d46b7a3d5a56006ae77b215fc69bc0', 518764441006038::numeric(78, 0)),
        ('ethereum', 'prod', 10449050::bigint, '\x35d8949372d46b7a3d5a56006ae77b215fc69bc0', 518764441006038::numeric(78, 0)),
        ('ethereum', 'prod', 10449051::bigint, '\x35d8949372d46b7a3d5a56006ae77b215fc69bc0', 518764441006038::numeric(78, 0)),
        ('ethereum', 'prod', 10449053::bigint, '\x35d8949372d46b7a3d5a56006ae77b215fc69bc0', 518764441006038::numeric(78, 0)),
        ('ethereum', 'prod', 10449054::bigint, '\x35d8949372d46b7a3d5a56006ae77b215fc69bc0', 518764441006038::numeric(78, 0)),
        ('ethereum', 'prod', 10449055::bigint, '\x35d8949372d46b7a3d5a56006ae77b215fc69bc0', 518764441006038::numeric(78, 0)),
        ('ethereum', 'prod', 10449056::bigint, '\x35d8949372d46b7a3d5a56006ae77b215fc69bc0', 518764441006038::numeric(78, 0)),
        ('ethereum', 'prod', 10449057::bigint, '\x35d8949372d46b7a3d5a56006ae77b215fc69bc0', 518764441006038::numeric(78, 0)),
        ('ethereum', 'prod', 10449058::bigint, '\x35d8949372d46b7a3d5a56006ae77b215fc69bc0', 518764441006038::numeric(78, 0)),
        ('ethereum', 'prod', 10449060::bigint, '\x35d8949372d46b7a3d5a56006ae77b215fc69bc0', 518764441006038::numeric(78, 0)),
        ('ethereum', 'prod', 10449062::bigint, '\x35d8949372d46b7a3d5a56006ae77b215fc69bc0', 518764441006038::numeric(78, 0)),
        ('ethereum', 'prod', 10449063::bigint, '\x35d8949372d46b7a3d5a56006ae77b215fc69bc0', 518764441006038::numeric(78, 0)),
        ('ethereum', 'prod', 10449065::bigint, '\x35d8949372d46b7a3d5a56006ae77b215fc69bc0', 518764441006038::numeric(78, 0)),
        ('ethereum', 'prod', 10449066::bigint, '\x35d8949372d46b7a3d5a56006ae77b215fc69bc0', 518764441006038::numeric(78, 0)),
        ('ethereum', 'prod', 10449067::bigint, '\x35d8949372d46b7a3d5a56006ae77b215fc69bc0', 518764441006038::numeric(78, 0)),
        ('ethereum', 'prod', 10449069::bigint, '\x35d8949372d46b7a3d5a56006ae77b215fc69bc0', 518764441006038::numeric(78, 0)),
        ('ethereum', 'prod', 10449070::bigint, '\x35d8949372d46b7a3d5a56006ae77b215fc69bc0', 518764441006038::numeric(78, 0)),
        ('ethereum', 'prod', 10449071::bigint, '\x35d8949372d46b7a3d5a56006ae77b215fc69bc0', 518764441006038::numeric(78, 0)),
        ('ethereum', 'prod', 10449072::bigint, '\x35d8949372d46b7a3d5a56006ae77b215fc69bc0', 518764441006038::numeric(78, 0)),
        ('ethereum', 'prod', 10449073::bigint, '\x35d8949372d46b7a3d5a56006ae77b215fc69bc0', 518764441006038::numeric(78, 0)),
        ('ethereum', 'prod', 10449074::bigint, '\x35d8949372d46b7a3d5a56006ae77b215fc69bc0', 518764441006038::numeric(78, 0)),
        ('ethereum', 'prod', 10449075::bigint, '\x35d8949372d46b7a3d5a56006ae77b215fc69bc0', 518764441006038::numeric(78, 0)),
        ('ethereum', 'prod', 10449076::bigint, '\x35d8949372d46b7a3d5a56006ae77b215fc69bc0', 518764441006038::numeric(78, 0)),
        ('ethereum', 'prod', 10449080::bigint, '\x35d8949372d46b7a3d5a56006ae77b215fc69bc0', 518764441006038::numeric(78, 0)),
        ('ethereum', 'prod', 10449081::bigint, '\x35d8949372d46b7a3d5a56006ae77b215fc69bc0', 518764441006038::numeric(78, 0)),
        ('ethereum', 'prod', 10449082::bigint, '\x35d8949372d46b7a3d5a56006ae77b215fc69bc0', 518764441006038::numeric(78, 0)),
        ('ethereum', 'prod', 10449085::bigint, '\x35d8949372d46b7a3d5a56006ae77b215fc69bc0', 518764441006038::numeric(78, 0)),
        ('ethereum', 'prod', 10449086::bigint, '\x35d8949372d46b7a3d5a56006ae77b215fc69bc0', 518764441006038::numeric(78, 0)),
        ('ethereum', 'prod', 10449087::bigint, '\x35d8949372d46b7a3d5a56006ae77b215fc69bc0', 518764441006038::numeric(78, 0)),
        ('ethereum', 'prod', 10449089::bigint, '\x35d8949372d46b7a3d5a56006ae77b215fc69bc0', 518764441006038::numeric(78, 0)),
        ('ethereum', 'prod', 10449093::bigint, '\x35d8949372d46b7a3d5a56006ae77b215fc69bc0', 518764441006038::numeric(78, 0)),
        ('ethereum', 'prod', 10449094::bigint, '\x35d8949372d46b7a3d5a56006ae77b215fc69bc0', 518764441006038::numeric(78, 0)),
        ('ethereum', 'prod', 10449095::bigint, '\x35d8949372d46b7a3d5a56006ae77b215fc69bc0', 518764441006038::numeric(78, 0)),
        ('ethereum', 'prod', 10449096::bigint, '\x35d8949372d46b7a3d5a56006ae77b215fc69bc0', 518764441006038::numeric(78, 0)),
        ('ethereum', 'prod', 10449097::bigint, '\x35d8949372d46b7a3d5a56006ae77b215fc69bc0', 518764441006038::numeric(78, 0)),
        ('ethereum', 'prod', 10449099::bigint, '\x35d8949372d46b7a3d5a56006ae77b215fc69bc0', 518764441006038::numeric(78, 0)),
        ('ethereum', 'prod', 10449102::bigint, '\x35d8949372d46b7a3d5a56006ae77b215fc69bc0', 518764441006038::numeric(78, 0)),
        ('ethereum', 'prod', 10449103::bigint, '\x35d8949372d46b7a3d5a56006ae77b215fc69bc0', 518764441006038::numeric(78, 0)),
        ('ethereum', 'prod', 10449106::bigint, '\x35d8949372d46b7a3d5a56006ae77b215fc69bc0', 518764441006038::numeric(78, 0)),
        ('ethereum', 'prod', 10449108::bigint, '\x35d8949372d46b7a3d5a56006ae77b215fc69bc0', 518764441006038::numeric(78, 0)),
        ('ethereum', 'prod', 10449110::bigint, '\x35d8949372d46b7a3d5a56006ae77b215fc69bc0', 518764441006038::numeric(78, 0)),
        ('ethereum', 'prod', 10449115::bigint, '\x35d8949372d46b7a3d5a56006ae77b215fc69bc0', 518764441006038::numeric(78, 0)),
        ('ethereum', 'prod', 10449116::bigint, '\x35d8949372d46b7a3d5a56006ae77b215fc69bc0', 518764441006038::numeric(78, 0)),
        ('ethereum', 'prod', 10449117::bigint, '\x35d8949372d46b7a3d5a56006ae77b215fc69bc0', 518764441006038::numeric(78, 0)),
        ('ethereum', 'prod', 10449118::bigint, '\x35d8949372d46b7a3d5a56006ae77b215fc69bc0', 518764441006038::numeric(78, 0)),
        ('ethereum', 'prod', 10449119::bigint, '\x35d8949372d46b7a3d5a56006ae77b215fc69bc0', 518764441006038::numeric(78, 0)),
        ('ethereum', 'prod', 10449125::bigint, '\x35d8949372d46b7a3d5a56006ae77b215fc69bc0', 518764441006038::numeric(78, 0)),
        ('ethereum', 'prod', 10449126::bigint, '\x35d8949372d46b7a3d5a56006ae77b215fc69bc0', 518764441006038::numeric(78, 0)),
        ('ethereum', 'prod', 10449127::bigint, '\x35d8949372d46b7a3d5a56006ae77b215fc69bc0', 518764441006038::numeric(78, 0)),
        ('ethereum', 'prod', 10449128::bigint, '\x35d8949372d46b7a3d5a56006ae77b215fc69bc0', 518764441006038::numeric(78, 0)),
        ('ethereum', 'prod', 10449129::bigint, '\x35d8949372d46b7a3d5a56006ae77b215fc69bc0', 518764441006038::numeric(78, 0)),
        ('ethereum', 'prod', 10449130::bigint, '\x35d8949372d46b7a3d5a56006ae77b215fc69bc0', 518764441006038::numeric(78, 0)),
        ('ethereum', 'prod', 10449132::bigint, '\x35d8949372d46b7a3d5a56006ae77b215fc69bc0', 518764441006038::numeric(78, 0)),
        ('ethereum', 'prod', 10449133::bigint, '\x35d8949372d46b7a3d5a56006ae77b215fc69bc0', 518764441006038::numeric(78, 0)),
        ('ethereum', 'prod', 10449134::bigint, '\x35d8949372d46b7a3d5a56006ae77b215fc69bc0', 518764441006038::numeric(78, 0)),
        ('ethereum', 'prod', 10449135::bigint, '\x35d8949372d46b7a3d5a56006ae77b215fc69bc0', 518764441006038::numeric(78, 0)),
        ('ethereum', 'prod', 10449136::bigint, '\x35d8949372d46b7a3d5a56006ae77b215fc69bc0', 518764441006038::numeric(78, 0)),
        ('ethereum', 'prod', 10449139::bigint, '\x35d8949372d46b7a3d5a56006ae77b215fc69bc0', 518764441006038::numeric(78, 0)),
        ('ethereum', 'prod', 10449140::bigint, '\x35d8949372d46b7a3d5a56006ae77b215fc69bc0', 518764441006038::numeric(78, 0)),
        ('ethereum', 'prod', 10449142::bigint, '\x35d8949372d46b7a3d5a56006ae77b215fc69bc0', 518764441006038::numeric(78, 0)),
        ('ethereum', 'prod', 10449144::bigint, '\x35d8949372d46b7a3d5a56006ae77b215fc69bc0', 518764441006038::numeric(78, 0)),
        ('ethereum', 'prod', 10449145::bigint, '\x35d8949372d46b7a3d5a56006ae77b215fc69bc0', 518764441006038::numeric(78, 0)),
        ('ethereum', 'prod', 10449146::bigint, '\x35d8949372d46b7a3d5a56006ae77b215fc69bc0', 518764441006038::numeric(78, 0)),
        ('ethereum', 'prod', 10449147::bigint, '\x35d8949372d46b7a3d5a56006ae77b215fc69bc0', 518764441006038::numeric(78, 0)),
        ('ethereum', 'prod', 10449148::bigint, '\x35d8949372d46b7a3d5a56006ae77b215fc69bc0', 518764441006038::numeric(78, 0)),
        ('ethereum', 'prod', 10449149::bigint, '\x35d8949372d46b7a3d5a56006ae77b215fc69bc0', 518764441006038::numeric(78, 0)),
        ('ethereum', 'prod', 10449150::bigint, '\x35d8949372d46b7a3d5a56006ae77b215fc69bc0', 518764441006038::numeric(78, 0)),
        ('ethereum', 'prod', 10449151::bigint, '\x35d8949372d46b7a3d5a56006ae77b215fc69bc0', 518764441006038::numeric(78, 0)),
        ('ethereum', 'prod', 10449152::bigint, '\x35d8949372d46b7a3d5a56006ae77b215fc69bc0', 518764441006038::numeric(78, 0)),
        ('ethereum', 'prod', 10449154::bigint, '\x35d8949372d46b7a3d5a56006ae77b215fc69bc0', 518764441006038::numeric(78, 0)),
        ('ethereum', 'prod', 10449157::bigint, '\x35d8949372d46b7a3d5a56006ae77b215fc69bc0', 518764441006038::numeric(78, 0)),
        ('ethereum', 'prod', 10449158::bigint, '\x35d8949372d46b7a3d5a56006ae77b215fc69bc0', 518764441006038::numeric(78, 0)),
        ('ethereum', 'prod', 10449159::bigint, '\x35d8949372d46b7a3d5a56006ae77b215fc69bc0', 518764441006038::numeric(78, 0)),
        ('ethereum', 'prod', 10449160::bigint, '\x35d8949372d46b7a3d5a56006ae77b215fc69bc0', 518764441006038::numeric(78, 0)),
        ('ethereum', 'prod', 10449161::bigint, '\x35d8949372d46b7a3d5a56006ae77b215fc69bc0', 518764441006038::numeric(78, 0)),
        ('ethereum', 'prod', 10449162::bigint, '\x35d8949372d46b7a3d5a56006ae77b215fc69bc0', 518764441006038::numeric(78, 0)),
        ('ethereum', 'prod', 10449163::bigint, '\x35d8949372d46b7a3d5a56006ae77b215fc69bc0', 518764441006038::numeric(78, 0)),

        ----------- USD0++ fix done -----------

        -- correction only relevant for the tests in the test_batch_rewards.py file
        ('ethereum', 'prod', 53::bigint, '\x02'::bytea, 500000000000000::numeric(78, 0))

    ) as temp(blockchain, environment, auction_id, token, price)
    where blockchain = '{{blockchain}}' and environment = '{{environment}}'
),
