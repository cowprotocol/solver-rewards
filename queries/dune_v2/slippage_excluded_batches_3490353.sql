-- https://github.com/cowprotocol/solver-rewards/pull/350
-- Query Here: https://dune.com/queries/3490353
select DISTINCT
  tx_hash
from
  cow_protocol_ethereum.trades
where
  0xf5d669627376ebd411e34b98f19c868c8aba5ada in (buy_token_address, sell_token_address) -- exclude AXS (Old)
  -- mixed ERC20/ERC721 tokens:
  or 0xf66434c34f3644473d91f065bF35225aec9e0Cfd in (buy_token_address, sell_token_address) -- exclude 404
  or 0x9E9FbDE7C7a83c43913BddC8779158F1368F0413 in (buy_token_address, sell_token_address) -- exclude PANDORA
  or 0x6C061D18D2b5bbfBe8a8D1EEB9ee27eFD544cC5D in (buy_token_address, sell_token_address) -- exclude MNRCH
  or 0xbE33F57f41a20b2f00DEc91DcC1169597f36221F in (buy_token_address, sell_token_address) -- exclude Rug
  or 0x938403C5427113C67b1604d3B407D995223C2B78 in (buy_token_address, sell_token_address) -- exclude OOZ
  or 0x54832d8724f8581e7Cc0914b3A4e70aDC0D94872 in (buy_token_address, sell_token_address) -- exclude DN404
  -- Temporary exceptions for Feb 13..Feb20, 2024 are starting here
  or 0xB5C457dDB4cE3312a6C5a2b056a1652bd542a208 in (buy_token_address, sell_token_address) -- exclude EtherRock404
  or 0xd555498a524612c67f286dF0e0a9a64a73a7Cdc7 in (buy_token_address, sell_token_address) -- exclude DeFrogs
  or 0x73576A927Cd93a578a9dFD61c75671D97c779da7 in (buy_token_address, sell_token_address) -- exclude Forge
  or 0x3F73EAEBA8f2b2699D6cC7581678bA631de5F183 in (buy_token_address, sell_token_address) -- exclude DEV404
  or 0x7c6314cCd4e34346Ba9C9bd9900FaafB4E3711B0 in (buy_token_address, sell_token_address) -- exclude ERC404X
  or 0xe2f95ee8B72fFed59bC4D2F35b1d19b909A6e6b3 in (buy_token_address, sell_token_address) -- exclude EGGX
  or 0xd5C02bB3e40494D4674778306Da43a56138A383E in (buy_token_address, sell_token_address) -- exclude OMNI404
  or 0x92715b8F93729c0B014213f769EF493baecEDACC in (buy_token_address, sell_token_address) -- exclude WIFU 404 
  or 0x413530a7beB9Ff6C44e9e6C9001C93B785420C32 in (buy_token_address, sell_token_address) -- exclude PFPAsia. NEEDS TO BE REMOVED FROM THIS LIST
  or 0xe7468080c033cE50Dd09A22ad1E58D1BDA69E436 in (buy_token_address, sell_token_address) -- exclude YUMYUM. NEEDS TO BE REMOVED FROM THIS LIST 
  or 0x83F20F44975D03b1b09e64809B757c47f942BEeA in (buy_token_address, sell_token_address) -- exclude sDAI -- NEEDS TO BE REMOVED FROM THIS LIST ASAP
  or tx_hash = 0x41418cef26e608ed47a5c4997833caaa2366a0163173286140da28a32e37b25d -- temporary solution
  or tx_hash = 0xdf415f3048d401c9ca7bf079722be96aaed3d2d2b5c0e12b7dc75d6eec30b3d4 -- temporary solution
  or tx_hash = 0x15b9906aa2039ccbc9ae9fab0f0c7517e9c88c41b74cd8a09f202803d37f6341 -- temporary solution
  or tx_hash = 0x3a71df0f6898b229c3643d4703b56d7510d455c65649cb364e5b69cadf5d1d37 -- temporary solution
  or tx_hash = 0xc9bcb4c8c68d4edcb97403131d28416a418ae537c43e9feca50f11ca744c079e -- temporary solution
  -- the following 2 stable-to-stable trades Otex settled. Due to inaccurate accounting, and since Otex has more of those, 
  -- I decided to remove 2 of those to mitigate the inaccuracies resulting from the rest
  or tx_hash = 0x60157b1891dbdbcdc88c637079c4c9e37d5fe943bf3ffff14412b33bf7125ad1
  or tx_hash = 0x414e72fa7c061a1b2c5905f21e41d8cb5500ec9043b65b317cd20362f4eff757
  or tx_hash = 0x829d0583b647581cdd8f01f62e6715a7c6333b499f164995601217bde1976a09 -- internalization involving PANDORA
  -- for week of Feb 27, 2024 until March 5, 2024
  or tx_hash = 0xc27463c9c6084a1067488d75732d37d85bf34f5d7882222eceba2d7f83c85dfe
  or tx_hash = 0x65ae7ff7419777bb0e81ebfffc55da654c89834f23065f7e62aac5891a8e0abb
  or tx_hash = 0xf82ad7fc31169a51e24f30677cf6ba5c337fd3c501551635cd94b768c9a1d5b1
  or tx_hash = 0xe3cf17ab69ff9efd72d44cd855db35c76732895a5413d13851871e2f6cbe701c
  or tx_hash = 0xdcddf86f9439522158c259ad5eabc6574b4f176631b09a27f450f2c6cc420993
  or tx_hash = 0xc3e8f21faea641132927eb9e7c5f5321cb90ef50300bce896a4277ee9a2bbd1a
  or tx_hash = 0x5ae92778c6d18d8391ecf87a10e4de381e558bab0eb939a69d596801d47e8b97
  -- for week of March 5, 2024 until March 12, 2024
  or tx_hash = 0x245cad3a40ab34ae6a6e79e050ec6946d80b1a501b345412bd33a8e0df6a1ea6
  or tx_hash = 0xc2e44a4abcfb719b3038ac346b89b2fd1391abcc3d9938954a6bc81495143619
  or tx_hash = 0xc7928590347245ccaa1b4794cc348c0d72b757f4376c023a8f67238c81280046
  or tx_hash = 0x3fbcf3aa9024d82e23c262a1e3c8ecbca83279e92fd0e2e147f3125762ca1bb4
  or tx_hash = 0x98d74de9f96d14f38cdabda0446d61e7a49db68f71670f1e66830bf40a0ca003
  or tx_hash = 0xaf56355b74863b9129824fbf31a182bc54bd94501b6c557778f060a2c2cd9973
  or tx_hash = 0x44daaccec0c6718b557258348b9f8736fbb94ea97d7d21336c8e0da3e309f84f
  or tx_hash = 0x5ae0810874dd9f4657fced144563af501e0d43265ac1b7a2ec2c7b0291b84af8
  or tx_hash = 0x5cb533bd94ac4c3703b6fe7e52c2089ffe9dc6675b2f6b96242a8b340cbd1430
  or tx_hash = 0xcde2671c02065773ef8efee2e39acb8a78bea213fffaf692f454e7bd97711c70
  or tx_hash = 0xe1d3480b3c99b2387cf6b0724abcd936fd7f888d9a5ee70be96cdcfc94eec29b
  or tx_hash = 0x0b8f6950f3f54034530bed401331172849b7e16bf964e3b92d838451a0a29d64
  or tx_hash = 0x1879438c38fae1ed205063218086cca0a600fe0263ab0f6cfad0f31bd3355b15
  or tx_hash = 0xbcfb968a772f0b68a7ecf1858925a2876e86a8d6941e7c53d0bf666aa66e02c0
  or tx_hash = 0xc06297f9a24faae8b165de7abf793dd53dfe8abd5be67ceb0964145a74e244cd
  or tx_hash = 0xb6e93c1b30b2020c943dd956ba5c797cecfbbdf121b0ee7ea1c0552b22e031a4
  or tx_hash = 0xcd9fb72ab8a61b6706e8ecb79939111318e770fcd8c29e8d49826c57b48cdb6b
  or tx_hash = 0x2a9a9b9c837bf8cd89dabf91825ca678fd2e2d506a0686cf3774e6c77748d319
  or tx_hash = 0xfb239a1959d1db58be3f33ab13c1aa45ea39e7b97653590b0f320b4e446ae6ab
  or tx_hash = 0x7b2588fda96cb480d6a055f327c368b3e1a5638f489e1b1ede9d143361b94c65
  or tx_hash = 0x00198fdad1047b31299d8d91afa71467cc491d643e730f9ef5bb9a9e7a5cfdad
  -- for week of March 12, 2024 until March 19, 2024
  or 0x382E57cA8e4c4DB9649884ca77B0a355692D14AC in (buy_token_address, sell_token_address) -- exclude XYXYX
  or tx_hash = 0x46c5064ffae9d4f0132fcaf9e75b169aecd23b0834b7743bc5280770ace3a10e
  or tx_hash = 0xba20e80f1e055865e594f868843f5f642b896291c91afa39cde1820e3129f543
  or tx_hash = 0xeb18483d07998f33952bba494aff9542283afcd2867b12fcfdc82672f87a97a3
  