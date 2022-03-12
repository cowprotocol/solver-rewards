results as (
    select
        solver_address,
        solver_name,
        sum(token_imbalance_wei * price / 10 ^ p.decimals) as usd_value,
        tx_hash
    from
        final_token_balance_sheet
        inner join end_prices p on token_from = p.contract_address
    group by
        solver_address,
        solver_name,
        tx_hash
    having
        sum(token_imbalance_wei) != 0
)(
    select
        *,
        (
            usd_value / (
                select
                    price
                from
                    prices."layer1_usd_eth"
                where
                    minute = '{{EndTime}}'
            ) * 10 ^ 18
        ) as eth_slippage_wei
    from
        results
    order by
        usd_value ASC
    limit
        5
)
UNION
all (
    select
        *,
        (
            usd_value / (
                select
                    price
                from
                    prices."layer1_usd_eth"
                where
                    minute = '{{EndTime}}'
            ) * 10 ^ 18
        ) as eth_slippage_wei
    from
        results
    order by
        usd_value DESC
    limit
        5
)