with trade_hashes as (
    select
        settlement.solver,
        t.block_number,
        order_uid,
        fee_amount,
        settlement.tx_hash,
        auction_id
    from
        trades as t
    left outer join lateral (
        select
            s.tx_hash,
            s.solver,
            s.auction_id,
            s.block_number,
            s.log_index
        from settlements as s
        where s.block_number = t.block_number and s.log_index > t.log_index
        order by s.log_index asc
        limit 1
    ) as settlement on true
    inner join settlement_observations as so
        on settlement.block_number = so.block_number and settlement.log_index = so.log_index
    where settlement.block_number >= {{start_block}} and settlement.block_number <= {{end_block}}
),

-- order data
order_data as (
    select
        uid,
        sell_token,
        buy_token,
        sell_amount,
        buy_amount,
        kind,
        app_data
    from orders
    union all
    select
        uid,
        sell_token,
        buy_token,
        sell_amount,
        buy_amount,
        kind,
        app_data
    from jit_orders
),

protocol_fee_kind as (
    select distinct on (fp.auction_id, fp.order_uid)
        fp.auction_id,
        fp.order_uid,
        fp.kind
    from fee_policies as fp inner join trade_hashes as th
        on fp.auction_id = th.auction_id and fp.order_uid = th.order_uid
    order by fp.auction_id, fp.order_uid, fp.application_order
),

-- unprocessed trade data
trade_data_unprocessed as (
    select
        ss.winner as solver,
        s.auction_id,
        s.tx_hash,
        t.order_uid,
        od.sell_token,
        od.buy_token,
        t.sell_amount, -- the total amount the user sends
        t.buy_amount, -- the total amount the user receives
        oe.executed_fee as observed_fee, -- the total discrepancy between what the user sends and what they would have send if they traded at clearing price
        od.kind,
        case
            when od.kind = 'sell' then od.buy_token
            when od.kind = 'buy' then od.sell_token
        end as surplus_token,
        cast(convert_from(ad.full_app_data, 'UTF8') as jsonb) -> 'metadata' -> 'partnerFee' ->> 'recipient' as partner_fee_recipient,
        coalesce(oe.protocol_fee_amounts[1], 0) as first_protocol_fee_amount,
        coalesce(oe.protocol_fee_amounts[2], 0) as second_protocol_fee_amount
    from
        settlements as s inner join settlement_scores as ss -- contains block_deadline
        on s.auction_id = ss.auction_id
    inner join trades as t -- contains traded amounts
        on s.block_number = t.block_number -- given the join that follows with the order execution table, this works even when multiple txs appear in the same block
    inner join order_data as od -- contains tokens and limit amounts
        on t.order_uid = od.uid
    inner join order_execution as oe -- contains executed fee
        on t.order_uid = oe.order_uid and s.auction_id = oe.auction_id
    left outer join app_data as ad -- contains full app data
        on od.app_data = ad.contract_app_data
    where s.block_number >= {{start_block}} and s.block_number <= {{end_block}}
),

-- processed trade data:
trade_data_processed as (
    select --noqa: ST06
        tdu.auction_id,
        tdu.solver,
        tdu.tx_hash,
        tdu.order_uid,
        tdu.sell_amount,
        tdu.buy_amount,
        tdu.sell_token,
        tdu.observed_fee,
        tdu.surplus_token,
        tdu.second_protocol_fee_amount,
        tdu.first_protocol_fee_amount + tdu.second_protocol_fee_amount as protocol_fee,
        tdu.partner_fee_recipient,
        case
            when tdu.partner_fee_recipient is not null then tdu.second_protocol_fee_amount
            else 0
        end as partner_fee,
        tdu.surplus_token as protocol_fee_token,
        pfk.kind as protocol_fee_kind
    from trade_data_unprocessed as tdu left outer join protocol_fee_kind as pfk
        on tdu.order_uid = pfk.order_uid and tdu.auction_id = pfk.auction_id
),

price_data as (
    select
        tdp.auction_id,
        tdp.order_uid,
        ap_surplus.price / pow(10, 18) as surplus_token_native_price,
        ap_protocol.price / pow(10, 18) as protocol_fee_token_native_price,
        ap_sell.price / pow(10, 18) as network_fee_token_native_price
    from trade_data_processed as tdp
    left outer join auction_prices as ap_sell -- contains price: sell token
        on tdp.auction_id = ap_sell.auction_id and tdp.sell_token = ap_sell.token
    left outer join auction_prices as ap_surplus -- contains price: surplus token
        on tdp.auction_id = ap_surplus.auction_id and tdp.surplus_token = ap_surplus.token
    left outer join auction_prices as ap_protocol -- contains price: protocol fee token
        on tdp.auction_id = ap_protocol.auction_id and tdp.surplus_token = ap_protocol.token
),

trade_data_processed_with_prices as (
    select --noqa: ST06
        tdp.auction_id,
        tdp.solver,
        tdp.tx_hash,
        tdp.order_uid,
        tdp.surplus_token,
        tdp.protocol_fee,
        tdp.protocol_fee_token,
        tdp.partner_fee,
        tdp.partner_fee_recipient,
        case
            when tdp.sell_token != tdp.surplus_token then tdp.observed_fee - (tdp.sell_amount - tdp.observed_fee) / tdp.buy_amount * coalesce(tdp.protocol_fee, 0)
            else tdp.observed_fee - coalesce(tdp.protocol_fee, 0)
        end as network_fee,
        tdp.sell_token as network_fee_token,
        surplus_token_native_price,
        protocol_fee_token_native_price,
        network_fee_token_native_price,
        protocol_fee_kind
    from
        trade_data_processed as tdp inner join price_data as pd
        on tdp.auction_id = pd.auction_id and tdp.order_uid = pd.order_uid
),

winning_quotes as (
    select --noqa: ST06
        concat('0x', encode(oq.solver, 'hex')) as quote_solver,
        oq.order_uid
    from trades as t inner join orders as o on order_uid = uid
    inner join order_quotes as oq on t.order_uid = oq.order_uid
    where
        (
            o.class = 'market'
            or (
                o.kind = 'sell'
                and (
                    oq.sell_amount - oq.gas_amount * oq.gas_price / oq.sell_token_price
                ) * oq.buy_amount >= o.buy_amount * oq.sell_amount
            )
            or (
                o.kind = 'buy'
                and o.sell_amount >= oq.sell_amount + oq.gas_amount * oq.gas_price / oq.sell_token_price
            )
        )
        and o.partially_fillable = 'f' -- the code above might fail for partially fillable orders
        and t.block_number >= {{start_block}}
        and t.block_number <= {{end_block}}
        and oq.solver != '\x0000000000000000000000000000000000000000'
) -- Most efficient column order for sorting would be having tx_hash or order_uid first

select
    '{{env}}' as environment,
    trade_hashes.auction_id,
    trade_hashes.block_number,
    concat('0x', encode(trade_hashes.order_uid, 'hex')) as order_uid,
    concat('0x', encode(trade_hashes.solver, 'hex')) as solver,
    quote_solver,
    concat('0x', encode(trade_hashes.tx_hash, 'hex')) as tx_hash,
    cast(coalesce(executed_fee, 0) as text) as surplus_fee,
    coalesce(reward, 0.0) as amount,
    cast(coalesce(cast(protocol_fee as numeric(78, 0)), 0) as text) as protocol_fee,
    case
        when protocol_fee_token is not null then concat('0x', encode(protocol_fee_token, 'hex'))
    end as protocol_fee_token,
    coalesce(protocol_fee_token_native_price, 0.0) as protocol_fee_native_price,
    cast(cast(oq.sell_amount as numeric(78, 0)) as text) as quote_sell_amount,
    cast(cast(oq.buy_amount as numeric(78, 0)) as text) as quote_buy_amount,
    oq.gas_amount * oq.gas_price as quote_gas_cost,
    oq.sell_token_price as quote_sell_token_price,
    cast(cast(coalesce(tdpwp.partner_fee, 0) as numeric(78, 0)) as text) as partner_fee,
    tdpwp.partner_fee_recipient,
    tdpwp.protocol_fee_kind
from trade_hashes left outer join order_execution as o
    on trade_hashes.order_uid = o.order_uid and trade_hashes.auction_id = o.auction_id
left outer join winning_quotes as wq on trade_hashes.order_uid = wq.order_uid
left outer join trade_data_processed_with_prices as tdpwp
    on trade_hashes.order_uid = tdpwp.order_uid and trade_hashes.auction_id = tdpwp.auction_id
left outer join order_quotes as oq on trade_hashes.order_uid = oq.order_uid
order by trade_hashes.block_number asc
