with -- For a permanent version of this query, please vist:
filtered_trades as (
    select
        t.block_time,
        t.tx_hash,
        solver_name,
        solver_address,
        trader as trader_in,
        receiver as trader_out,
        sell_token_address as "sellToken",
        buy_token_address as "buyToken",
        atoms_sold as "sellAmount",
        atoms_bought as "buyAmount",
        '\x9008D19f58AAbD9eD0D60971565AA8510560ab41' :: bytea as contract_address
    from
        gnosis_protocol_v2."trades" t
        join gnosis_protocol_v2."view_batches" b on t.tx_hash = b.tx_hash
    where
        b.block_time between '{{StartTime}}'
        and '{{EndTime}}'
        and case
            when '{{TxHash}}' = '0x' then true
            else replace('{{TxHash}}', '0x', '\x') :: bytea = t.tx_hash
        end
),
user_in as (
    select
        block_time,
        tx_hash,
        solver_address,
        solver_name,
        trader_in as sender,
        contract_address as receiver,
        "sellToken" as token,
        "sellAmount" as amount_wei,
        'IN User' as transfer_type
    from
        filtered_trades
),
user_out as (
    select
        block_time,
        tx_hash,
        solver_address,
        solver_name,
        contract_address as sender,
        trader_out as receiver,
        "buyToken" as token,
        "buyAmount" as amount_wei,
        'OUT User' as transfer_type
    from
        filtered_trades
),
other_transfers as (
    select
        block_time,
        tx_hash,
        solver_address,
        solver_name,
        "from" sender,
        "to" receiver,
        t.contract_address as token,
        value as amount_wei,
        case
            when "to" = '\x9008D19f58AAbD9eD0D60971565AA8510560ab41' -- beta contract
            then 'IN AMM'
            when "from" = '\x9008D19f58AAbD9eD0D60971565AA8510560ab41' -- beta contract
            then 'OUT AMM'
        end as transfer_type
    from
        erc20."ERC20_evt_Transfer" t
        inner join gnosis_protocol_v2."view_batches" b on evt_tx_hash = tx_hash
    where
        b.block_time between '{{StartTime}}'
        and '{{EndTime}}'
        and '\x9008D19f58AAbD9eD0D60971565AA8510560ab41' in ("to", "from")
        and "from" not in (
            select
                trader_in
            from
                filtered_trades
        )
        and "to" not in (
            select
                trader_out
            from
                filtered_trades
        )
        and case
            when '{{TxHash}}' = '0x' then true
            else replace('{{TxHash}}', '0x', '\x') :: bytea = b.tx_hash
        end
),
batch_transfers as (
    select
        *
    from
        user_in
    union
    all
    select
        *
    from
        user_out
    union
    all
    select
        *
    from
        other_transfers
),
incoming_and_outgoing as (
    SELECT
        block_time,
        tx_hash,
        CONCAT('0x', ENCODE(solver_address, 'hex')) as solver_address,
        solver_name,
        case
            when t.symbol = 'ETH' then 'WETH'
            when t.symbol is not null then t.symbol
            else text(token)
        end as symbol,
        case
            when token = '\xeeeeeeeeeeeeeeeeeeeeeeeeeeeeeeeeeeeeeeee' then '\xc02aaa39b223fe8d0a0e5c4f27ead9083c756cc2'
            else token
        end as token_from,
        null :: bytea as token_to,
        case
            when receiver = '\x9008D19f58AAbD9eD0D60971565AA8510560ab41' -- beta contract
            then amount_wei
            when sender = '\x9008D19f58AAbD9eD0D60971565AA8510560ab41' -- beta contract
            then -1 * amount_wei
        end as amount_from,
        null :: numeric as amount_to,
        transfer_type
    from
        batch_transfers i
        left outer join erc20.tokens t on i.token = t.contract_address
),
pre_clearing_prices as (
    select
        call_tx_hash as tx_hash,
        unnest("clearingPrices") as price,
        unnest(tokens) as token
    from
        gnosis_protocol_v2."GPv2Settlement_call_settle"
    where
        call_success = true
        and call_block_time between '{{StartTime}}'
        and '{{EndTime}}'
    order by
        call_block_number desc
),
clearing_prices as (
    select
        tx_hash,
        price as clearing_price,
        case
            when token = '\xeeeeeeeeeeeeeeeeeeeeeeeeeeeeeeeeeeeeeeee' then '\xc02aaa39b223fe8d0a0e5c4f27ead9083c756cc2'
            else token
        end as token
    from
        pre_clearing_prices
),
potential_buffer_trades as (
    select
        block_time,
        tx_hash,
        solver_address,
        solver_name,
        symbol,
        token_from,
        sum(amount_from) as amount_from
    from
        incoming_and_outgoing io
    group by
        tx_hash,
        solver_address,
        solver_name,
        symbol,
        token_from,
        block_time
    having
        abs(sum(amount_from)) > 0.0001 -- exclude 0 to prevent zero division, and exclude very small values for performance
),
valued_potential_buffered_trades as (
    select
        t.*,
        amount_from * clearing_price as clearing_value,
        amount_from / 10 ^ decimals * price as usd_value
    from
        potential_buffer_trades t
        left outer join clearing_prices cp on t.tx_hash = cp.tx_hash
        and t.token_from = cp.token
        left outer join prices.usd pusd on pusd.contract_address = t.token_from
        and date_trunc('minute', block_time) = pusd.minute
),
buffer_trades as (
    Select
        date(a.block_time) as block_time,
        a.tx_hash,
        a.solver_address,
        a.solver_name,
        a.symbol,
        a.token_from as token_from,
        b.token_from as token_to,
        -1 * a.amount_from as amount_from,
        -1 * b.amount_from as amount_to,
        'INTERNAL_TRADE' as transfer_type
    from
        valued_potential_buffered_trades a full
        outer join valued_potential_buffered_trades b on a.tx_hash = b.tx_hash
    where
        (
            case
                when a.clearing_value is not null
                and b.clearing_value is not null then abs(
                    (a.clearing_value + b.clearing_value) / (abs(a.clearing_value) + abs(b.clearing_value))
                ) < 0.015 -- clearing prices are much more accurate, hence a lower tolerance was chosen
                else case
                    when a.usd_value is not null
                    and b.usd_value is not null then abs(
                        (a.usd_value + b.usd_value) / (abs(a.usd_value) + abs(b.usd_value))
                    ) < 0.10 -- prices.usd are not so accurate, hence we use bigger tolerance
                    else false
                end
            end
        )
),
incoming_and_outgoing_with_buffer_trades as (
    select
        *
    from
        incoming_and_outgoing
    union
    all
    select
        *
    from
        buffer_trades
),
final_token_balance_sheet as (
    select
        solver_address,
        solver_name,
        sum(amount_from) token_imbalance_wei,
        symbol,
        token_from,
        tx_hash
    from
        incoming_and_outgoing_with_buffer_trades
    group by
        symbol,
        token_from,
        solver_address,
        solver_name,
        tx_hash
),
end_prices as (
    select
        median_price as price,
        p_complete.contract_address,
        decimals
    from
        prices.prices_from_dex_data p_complete
    where
        p_complete.hour = '{{EndTime}}'
)