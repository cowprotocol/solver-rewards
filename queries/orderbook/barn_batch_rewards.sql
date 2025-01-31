with observed_settlements as (
    select --noqa: ST06
        -- settlement
        tx_hash,
        solver,
        s.block_number,
        -- settlement_observations
        effective_gas_price * gas_used as execution_cost,
        surplus,
        s.auction_id
    from settlements as s inner join settlement_observations as so
        on s.block_number = so.block_number and s.log_index = so.log_index
    inner join settlement_scores as ss on s.auction_id = ss.auction_id
    where ss.block_deadline >= {{start_block}} and ss.block_deadline <= {{end_block}}
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
    union distinct -- A _distinct_ union is needed since orders can appear in the normal orders
    -- table and in the jit orders table. Since the uid is otherwise unique, no valid order is
    -- removed by the _distinct_ union.
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

-- unprocessed trade data
trade_data_unprocessed as (
    select --noqa: ST06
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
    from settlements as s inner join settlement_scores as ss -- contains block_deadline
        on s.auction_id = ss.auction_id
    inner join trades as t -- contains traded amounts
        on s.block_number = t.block_number -- given the join that follows with the order execution table, this works even when multiple txs appear in the same block
    inner join order_data as od -- contains tokens and limit amounts
        on t.order_uid = od.uid
    inner join order_execution as oe -- contains executed fee
        on t.order_uid = oe.order_uid and s.auction_id = oe.auction_id
    left outer join app_data as ad -- contains full app data
        on od.app_data = ad.contract_app_data
    where ss.block_deadline >= {{start_block}} and ss.block_deadline <= {{end_block}}
),

-- processed trade data:
trade_data_processed as (
    select --noqa: ST06
        auction_id,
        solver,
        tx_hash,
        order_uid,
        sell_amount,
        buy_amount,
        sell_token,
        observed_fee,
        surplus_token,
        second_protocol_fee_amount,
        first_protocol_fee_amount + second_protocol_fee_amount as protocol_fee,
        partner_fee_recipient,
        case
            when partner_fee_recipient is not null then second_protocol_fee_amount
            else 0
        end as partner_fee,
        surplus_token as protocol_fee_token
    from trade_data_unprocessed
),

price_data as (
    select
        tdp.auction_id,
        tdp.order_uid,
        ap_surplus.price / pow(10, 18) as surplus_token_native_price,
        ap_protocol.price / pow(10, 18) as protocol_fee_token_native_price,
        ap_sell.price / pow(10, 18) as network_fee_token_native_price
    from trade_data_processed as tdp left outer join auction_prices as ap_sell -- contains price: sell token
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
        network_fee_token_native_price
    from trade_data_processed as tdp inner join price_data as pd
        on tdp.auction_id = pd.auction_id and tdp.order_uid = pd.order_uid
),

batch_protocol_fees as (
    select
        solver,
        tx_hash,
        sum(protocol_fee * protocol_fee_token_native_price) as protocol_fee
    from trade_data_processed_with_prices
    group by solver, tx_hash
),

batch_network_fees as (
    select
        solver,
        tx_hash,
        sum(network_fee * network_fee_token_native_price) as network_fee
    from trade_data_processed_with_prices
    group by solver, tx_hash
),

reward_data as (
    select --noqa: ST06
        -- observations
        ss.auction_id,
        os.tx_hash,
        -- TODO - assuming that `solver == winner` when both not null
        --  We will need to monitor that `solver == winner`!
        ss.winner as solver,
        block_number as settlement_block,
        block_deadline,
        coalesce(execution_cost, 0) as execution_cost,
        coalesce(surplus, 0) as surplus,
        -- scores
        winning_score,
        case
            when block_number is not null and block_number <= block_deadline then winning_score
            else 0
        end as observed_score,
        reference_score,
        -- protocol_fees
        coalesce(cast(protocol_fee as numeric(78, 0)), 0) as protocol_fee,
        coalesce(cast(network_fee as numeric(78, 0)), 0) as network_fee
    from settlement_scores as ss
    -- outer joins made in order to capture non-existent settlements.
    left outer join observed_settlements as os on ss.auction_id = os.auction_id
    left outer join batch_protocol_fees as bpf on os.tx_hash = bpf.tx_hash
    left outer join batch_network_fees as bnf on os.tx_hash = bnf.tx_hash
    where ss.block_deadline >= {{start_block}} and ss.block_deadline <= {{end_block}}
),

reward_per_auction as (
    select
        tx_hash,
        auction_id,
        settlement_block,
        block_deadline,
        solver,
        execution_cost,
        surplus,
        protocol_fee, -- the protocol fee
        network_fee, -- the network fee
        observed_score - reference_score as uncapped_payment,
        -- Capped Reward = CLAMP_[-E, E + exec_cost](uncapped_reward_eth)
        least(
            greatest(
                -{{EPSILON_LOWER}},
                observed_score - reference_score
            ),
            {{EPSILON_UPPER}}
        ) as capped_payment,
        winning_score,
        reference_score
    from reward_data
),

dune_sync_batch_data_table as ( --noqa: ST03
    select --noqa: ST06
        'barn' as environment,
        auction_id,
        settlement_block as block_number,
        block_deadline,
        case
            when tx_hash is null then null
            else concat('0x', encode(tx_hash, 'hex'))
        end as tx_hash,
        concat('0x', encode(solver, 'hex')) as solver,
        execution_cost,
        surplus,
        protocol_fee,
        network_fee,
        uncapped_payment as uncapped_payment_eth,
        capped_payment,
        winning_score,
        reference_score
    from reward_per_auction
    order by block_deadline
),

primary_rewards as (
    select
        solver,
        sum(capped_payment) as payment,
        sum(protocol_fee) as protocol_fee,
        sum(network_fee) as network_fee
    from reward_per_auction
    group by solver
),

partner_fees_per_solver as (
    select
        solver,
        partner_fee_recipient,
        sum(partner_fee * protocol_fee_token_native_price) as partner_fee
    from trade_data_processed_with_prices
    where partner_fee_recipient is not null
    group by solver, partner_fee_recipient
),

aggregate_partner_fees_per_solver as (
    select
        solver,
        array_agg(partner_fee_recipient) as partner_list,
        array_agg(partner_fee) as partner_fee
    from partner_fees_per_solver
    group by solver
),

aggregate_results as (
    select --noqa: ST06
        concat('0x', encode(pr.solver, 'hex')) as solver,
        coalesce(payment, 0) as primary_reward_eth,
        coalesce(protocol_fee, 0) as protocol_fee_eth,
        coalesce(network_fee, 0) as network_fee_eth,
        partner_list,
        partner_fee as partner_fee_eth
    from primary_rewards as pr left outer join aggregate_partner_fees_per_solver as aif on pr.solver = aif.solver
),

solver_rewards_script_table as (
    select *
    from aggregate_results
    order by solver
)

select * from {{results}}
