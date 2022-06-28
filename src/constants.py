"""Temporary constant for merging transfers and slippages."""
# This mapping is in the form name -> (OldSolver, NewSolver)
# Created manually with this dune query:
# select
#     concat(environment, '-', name) as solver_name,
#     concat('0x', encode(address, 'hex')) as address,
#     active
# from gnosis_protocol_v2."view_solvers"
# where environment = 'prod'
# order by name, active
MERGE_DATA = {
    "prod-Otex": (
        "0x6fa201c3aff9f1e4897ed14c7326cf27548d9c35",
        "0xc9ec550bea1c64d779124b23a26292cc223327b6",
    ),
    "prod-Baseline": (
        "0x833f076d182123ca8dde2743045ea02957bd61ef",
        "0x3cee8c7d9b5c8f225a8c36e7d3514e1860309651",
    ),
    "prod-Naive": (
        "0x340185114f9d2617dc4c16088d0375d09fee9186",
        "0x7a0a8890d71a4834285efdc1d18bb3828e765c6a",
    ),
    "prod-DexCowAgg": (
        "0x2d15894fac906386ff7f4bd07fceac43fcf80c73",
        "0x6d1247b8acf4dfd5ff8cfd6c47077ddc43d4500e",
    ),
    "prod-ParaSwap": (
        "0x15f4c337122ec23859ec73bec00ab38445e45304",
        "0xe9ae2d792f981c53ea7f6493a17abf5b2a45a86b",
    ),
    "prod-Legacy": (
        "0xa6ddbd0de6b310819b49f680f65871bee85f517e",
        "0x0e8f282ce027f3ac83980e6020a2463f4c841264",
    ),
    "prod-PLM": (
        "0xe58c68679e7aab8ef83bf37e88b18eb1f6e30e22",
        "0x149d0f9282333681ee41d30589824b2798e9fb47",
    ),
    "prod-QuasiModo": (
        "0x77ec2a722c2393d3fd64617bbaf1499c713e616b",
        "0x731a0a8ab2c6fcad841e82d06668af7f18e34970",
    ),
    "prod-BalancerSOR": (
        "0xa97def4fbcba3b646dd169bc2eee40f0f3fe7771",
        "0xf7995b6b051166ea52218c37b8d03a2a6bbef3da",
    ),
    "prod-0x": (
        "0xe92f359e6f05564849afa933ce8f62b8007a1d5d",
        "0xda869be4adea17ad39e1dfece1bc92c02491504f",
    ),
    "prod-MIP": (
        "0xf2d21ad3c88170d4ae52bbbeba80cb6078d276f4",
        "0xe8ff24ec26bd46e0140d1824da44efad2a0920b5",
    ),
    "prod-1inch": (
        "0xde1c59bc25d806ad9ddcbe246c4b5e5505645718",
        "0xb20b86c4e6deeb432a22d773a221898bbbd03036",
    ),
}
