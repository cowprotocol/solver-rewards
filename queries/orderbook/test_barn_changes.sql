with auction_info as materialized (
    select
        id as auction_id,
        deadline as block_deadline
    from competition_auctions
    where deadline >= 22620415 and deadline <= 22670450
),

new_settlement_scores_prelim as ( -- here we assume at most one winning solutions per solver
    select
        ai.auction_id,
        ai.block_deadline,
        ps.solver as winner,
        ps.score as winning_score,
        rs.reference_score
    from auction_info as ai inner join proposed_solutions as ps
        on ai.auction_id = ps.auction_id
    inner join reference_scores as rs
        on ai.auction_id = rs.auction_id and ps.solver = rs.solver
    where ps.is_winner = true
),

auction_scores as (
    select
        auction_id,
        sum(winning_score) as auction_score
    from new_settlement_scores_prelim
    group by auction_id

),

new_settlement_scores as materialized (
    select
        nssp.*,
        aus.auction_score
    from new_settlement_scores_prelim as nssp inner join auction_scores as aus
        on nssp.auction_id = aus.auction_id
),

observed_settlements as (
    select --noqa: ST06
        -- settlement
        s.auction_id,
        s.tx_hash,
        s.solver,
        s.block_number,
        -- settlement_observations
        effective_gas_price * gas_used as execution_cost,
        surplus
    from settlements as s inner join settlement_observations as so
        on s.block_number = so.block_number and s.log_index = so.log_index
    inner join auction_info as ai on s.auction_id = ai.auction_id
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

settlements_with_previous as (
    -- for each settlement, calculate the previous settlement's log_index within the same block
    select --noqa: ST06
        s.tx_hash,
        s.block_number,
        s.log_index as settlement_log_index,
        lag(s.log_index) over (
            partition by block_number
            order by log_index
        ) as previous_settlement_log_index,
        s.solver,
        s.auction_id,
        s.solution_uid
    from settlements as s inner join auction_info as ai on
        s.auction_id = ai.auction_id
),

trade_settlement_matching as (
    -- match each trade to the settlement that happens immediately after it
    select
        t.block_number,
        t.order_uid,
        t.log_index as trade_log_index,
        t.sell_amount,
        t.buy_amount,
        t.fee_amount,
        s.tx_hash,
        s.settlement_log_index,
        s.solver,
        s.auction_id,
        s.solution_uid
    from trades as t inner join settlements_with_previous as s
        on t.block_number = s.block_number
    where
        -- the trade log_index must be greater than the previous settlement (or no previous settlement exists)
        (t.log_index > coalesce(s.previous_settlement_log_index, -1))
        -- the trade log_index must be less than or equal to the current settlement
        and t.log_index <= s.settlement_log_index
),

-- unprocessed trade data
trade_data_unprocessed as (
    select --noqa: ST06
        tsm.solver,
        tsm.auction_id,
        tsm.tx_hash,
        tsm.order_uid,
        od.sell_token,
        od.buy_token,
        tsm.sell_amount, -- the total amount the user sends
        tsm.buy_amount, -- the total amount the user receives
        oe.executed_fee as observed_fee, -- the total discrepancy between what the user sends and what they would have send if they traded at clearing price
        od.kind,
        case
            when od.kind = 'sell' then od.buy_token
            when od.kind = 'buy' then od.sell_token
        end as surplus_token,
        cast(convert_from(ad.full_app_data, 'UTF8') as jsonb) -> 'metadata' -> 'partnerFee' ->> 'recipient' as partner_fee_recipient,
        cast(convert_from(ad.full_app_data, 'UTF8') as jsonb) ->> 'appCode' as app_code,
        coalesce(oe.protocol_fee_amounts[1], 0) as first_protocol_fee_amount,
        coalesce(oe.protocol_fee_amounts[2], 0) as second_protocol_fee_amount
    from trade_settlement_matching as tsm inner join new_settlement_scores as ss -- contains block_deadline
        on tsm.auction_id = ss.auction_id and tsm.solver = ss.winner
    inner join order_execution as oe -- contains executed fee
        on tsm.order_uid = oe.order_uid and tsm.auction_id = oe.auction_id
    inner join order_data as od -- contains tokens and limit amounts
        on oe.order_uid = od.uid
    left outer join app_data as ad -- contains full app data
        on od.app_data = ad.contract_app_data
    where ss.block_deadline >= 22620415 and ss.block_deadline <= 22670450
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
        app_code,
        case
            when partner_fee_recipient is not null then second_protocol_fee_amount
            else 0
        end as partner_fee,
        surplus_token as protocol_fee_token
    from trade_data_unprocessed
),

----- the auction_prices_corrections and excluded_auctions tables are filled with dummy entries here
auction_prices_corrections (blockchain, environment, auction_id, token, price) as (
    select *
    from (
        values
        ('ethereum', 'prod', 10105330::bigint, '\xad038eb671c44b853887a7e32528fab35dc5d710'::bytea, 43314929461672::numeric(78, 0))  --noqa: CV11
    ) as temp (blockchain, environment, auction_id, token, price)  --noqa: RF04
),

excluded_auctions (blockchain, environment, auction_id) as (
    select
        *,
        0 as multiplier
    from (
        values ('base', 'prod', 24280706::bigint) --noqa: CV11
    ) as temp (blockchain, environment, auction_id) --noqa: RF04
),

auction_prices_processed as (
    select distinct on (ap.auction_id, ap.token) -- this is needed due to the inner join with the observed_settlements in case of multiple winners per auction_id
        ap.auction_id,
        ap.token,
        coalesce(apc.price, ap.price) as price
    from auction_prices as ap inner join observed_settlements as os on ap.auction_id = os.auction_id -- inner join done to speed up query
    left outer join auction_prices_corrections as apc
        on ap.auction_id = apc.auction_id and ap.token = apc.token
),

price_data as (
    select
        tdp.order_uid,
        tdp.auction_id,
        ap_surplus.price / pow(10, 18) as surplus_token_native_price,
        ap_protocol.price / pow(10, 18) as protocol_fee_token_native_price,
        ap_sell.price / pow(10, 18) as network_fee_token_native_price
    from trade_data_processed as tdp left outer join auction_prices_processed as ap_sell -- contains price: sell token
        on tdp.auction_id = ap_sell.auction_id and tdp.sell_token = ap_sell.token
    left outer join auction_prices_processed as ap_surplus -- contains price: surplus token
        on tdp.auction_id = ap_surplus.auction_id and tdp.surplus_token = ap_surplus.token
    left outer join auction_prices_processed as ap_protocol -- contains price: protocol fee token
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
        tdp.app_code,
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
            when block_number is not null and block_number <= block_deadline then auction_score
            else auction_score - winning_score
        end as observed_score,
        reference_score,
        -- protocol_fees
        coalesce(cast(protocol_fee as numeric(78, 0)), 0) as protocol_fee,
        coalesce(cast(network_fee as numeric(78, 0)), 0) as network_fee,
        least(reference_score, auction_score) as reference_score_capped
    from new_settlement_scores as ss
    -- outer joins made in order to capture non-existent settlements.
    left outer join observed_settlements as os
        on ss.auction_id = os.auction_id and ss.winner = os.solver
    left outer join batch_protocol_fees as bpf on os.tx_hash = bpf.tx_hash and ss.winner = bpf.solver
    left outer join batch_network_fees as bnf on os.tx_hash = bnf.tx_hash and ss.winner = bnf.solver
    where ss.block_deadline >= 22620415 and ss.block_deadline <= 22670450
),

reward_per_auction as (
    select --noqa: ST06
        tx_hash,
        auction_id,
        settlement_block,
        block_deadline,
        solver,
        execution_cost,
        surplus,
        protocol_fee, -- the protocol fee
        network_fee, -- the network fee
        observed_score - reference_score_capped as uncapped_payment,
        -- Capped Reward = CLAMP_[-E, E + exec_cost](uncapped_reward_eth)
        least(
            greatest(
                -10000000000000000,
                observed_score - reference_score_capped
            ),
            12000000000000000
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

reward_per_auction_filtered as (
    select
        rpa.solver,
        rpa.protocol_fee,
        rpa.network_fee,
        rpa.capped_payment * coalesce(ea.multiplier, 1) as capped_payment
    from reward_per_auction as rpa left outer join excluded_auctions as ea on rpa.auction_id = ea.auction_id
),

primary_rewards as (
    select
        solver,
        sum(capped_payment) as payment,
        sum(protocol_fee) as protocol_fee,
        sum(network_fee) as network_fee
    from reward_per_auction_filtered
    group by solver
),

partner_fees_per_solver as (
    select
        solver,
        partner_fee_recipient,
        app_code,
        array[partner_fee_recipient, app_code] as recipient_app_code_pair,
        sum(partner_fee * protocol_fee_token_native_price) as partner_fee
    from trade_data_processed_with_prices
    where partner_fee_recipient is not null
    group by solver, partner_fee_recipient, app_code
),

aggregate_partner_fees_per_solver as (
    select
        solver,
        array_agg(recipient_app_code_pair) as partner_list,
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

solver_rewards_script_table as ( --noqa: ST03
    select *
    from aggregate_results
    order by solver
)

select * from dune_sync_batch_data_table;
