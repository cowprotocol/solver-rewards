select
    '0xDEf1CA1fb7FBcDC777520aa7f396b4E015F497aB' as token_address,
    concat('0x', encode(solver, 'hex')) as receiver,
    -- TODO - use `rewards` column in solver_competitions (when available)
    ((50 * count(distinct sc.tx_hash) + 35 * count(distinct order_uid)) * 10^18)::numeric::text as amount
from settlements
join solver_competitions sc
    on settlements.tx_hash = sc.tx_hash
join trades t on settlements.block_number = t.block_number
where settlements.block_number between {{start_block}} and {{end_block}}
group by solver
