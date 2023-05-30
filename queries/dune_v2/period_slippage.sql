-- https://github.com/cowprotocol/solver-rewards/pull/259
-- Query Here: https://dune.com/queries/2421375
with
batch_meta as (
    select b.block_time,
           b.block_number,
           b.tx_hash,
           case
            when dex_swaps = 0
            -- Estimation made here: https://dune.com/queries/1646084
                then cast((gas_used - 73688 - (70528 * num_trades)) / 90000 as int)
                else dex_swaps
           end as dex_swaps,
           num_trades,
           b.solver_address
    from cow_protocol_ethereum.batches b
    where b.block_time between cast('{{StartTime}}' as timestamp) and cast('{{EndTime}}' as timestamp)
    and (b.solver_address = from_hex('{{SolverAddress}}') or '{{SolverAddress}}' = '0x')
    and (b.tx_hash = from_hex('{{TxHash}}') or '{{TxHash}}' = '0x')
)
,filtered_trades as (
    select t.tx_hash,
           t.block_number,
           case
                when trader = 0x9008d19f58aabd9ed0d60971565aa8510560ab41
                then 0x0000000000000000000000000000000000000000
                else trader
           end as trader_in,
           receiver                                     as trader_out,
           sell_token_address                           as sell_token,
           buy_token_address                            as buy_token,
           atoms_sold - coalesce(surplus_fee, 0)        as atoms_sold,
           atoms_bought,
           0x9008d19f58aabd9ed0d60971565aa8510560ab41 as contract_address
    from cow_protocol_ethereum.trades t
         join cow_protocol_ethereum.batches b
            on t.block_number = b.block_number
            and t.tx_hash = b.tx_hash
    left outer join cow_protocol_ethereum.order_rewards f
        on f.tx_hash = t.tx_hash
        and f.order_uid = t.order_uid
    where b.block_time between cast('{{StartTime}}' as timestamp) and cast('{{EndTime}}' as timestamp)
    and t.block_time between cast('{{StartTime}}' as timestamp) and cast('{{EndTime}}' as timestamp)
    and (b.solver_address = from_hex('{{SolverAddress}}') or '{{SolverAddress}}' = '0x')
    and (t.tx_hash = from_hex('{{TxHash}}') or '{{TxHash}}' = '0x')
)
,batchwise_traders as (
    select
        tx_hash,
        block_number,
        array_agg(trader_in) as traders_in,
        array_agg(trader_out) as traders_out
    from filtered_trades
    group by tx_hash, block_number
)
,user_in as (
    select
        tx_hash,
        trader_in        as sender,
        contract_address as receiver,
        sell_token       as token,
        cast(atoms_sold as int256)       as amount_wei,
        'IN_USER'        as transfer_type
    from filtered_trades
)
,user_out as (
    select tx_hash,
          contract_address as sender,
          trader_out       as receiver,
          buy_token        as token,
          cast(atoms_bought as int256)            as amount_wei,
          'OUT_USER'       as transfer_type
    from filtered_trades
)
,other_transfers as (
    select b.tx_hash,
          "from"             as sender,
          to                 as receiver,
          t.contract_address as token,
          cast(value as int256) as amount_wei,
          case
              when to = 0x9008d19f58aabd9ed0d60971565aa8510560ab41
                  then 'IN_AMM'
              when "from" = 0x9008d19f58aabd9ed0d60971565aa8510560ab41
                  then 'OUT_AMM'
              end            as transfer_type
    from erc20_ethereum.evt_Transfer t
             inner join cow_protocol_ethereum.batches b
                on evt_block_number = b.block_number
                and evt_tx_hash = b.tx_hash
             inner join batchwise_traders bt
                on evt_tx_hash = bt.tx_hash
    where b.block_time between cast('{{StartTime}}' as timestamp) and cast('{{EndTime}}' as timestamp)
      and 0x9008d19f58aabd9ed0d60971565aa8510560ab41 in (to, "from")
      and not contains(traders_in, "from")
      and not contains(traders_out, to)
      and to != "from"
      and "from" not in ( -- ETH FLOW ORDERS ARE NOT AMM TRANSFERS!
          select distinct contract_address
          from cow_protocol_ethereum.CoWSwapEthFlow_evt_OrderPlacement
      )
      and (t.evt_tx_hash = from_hex('{{TxHash}}') or '{{TxHash}}' = '0x')
      and (solver_address = from_hex('{{SolverAddress}}') or '{{SolverAddress}}' = '0x')
)
,eth_transfers as (
    select
        bt.tx_hash,
        "from" as sender,
        to     as receiver,
        0xeeeeeeeeeeeeeeeeeeeeeeeeeeeeeeeeeeeeeeee as token,
        cast(value as int256) as amount_wei,
        case
          when 0x9008d19f58aabd9ed0d60971565aa8510560ab41 = to
          then 'AMM_IN'
          else 'AMM_OUT'
        end as transfer_type
    from batchwise_traders bt
    inner join ethereum.traces et
        on bt.block_number = et.block_number
        and bt.tx_hash = et.tx_hash
        and value > cast(0 as uint256)
        and success = true
    and 0x9008d19f58aabd9ed0d60971565aa8510560ab41 in (to, "from")
    -- WETH unwraps don't have cancelling WETH transfer.
    and "from" != 0xc02aaa39b223fe8d0a0e5c4f27ead9083c756cc2
    -- ETH transfers to traders are already part of USER_OUT
    and not contains(traders_out, to)
)
,pre_batch_transfers as (
    select * from (
        select * from user_in
        union all
        select * from user_out
        union all
        select * from other_transfers
        union all
        select * from eth_transfers
        ) as _
    order by tx_hash
)
,batch_transfers as (
    select
        block_time,
        block_number,
        pbt.tx_hash,
        dex_swaps,
        num_trades,
        solver_address,
        sender,
        receiver,
        token,
        amount_wei,
        transfer_type
    from batch_meta bm
    join pre_batch_transfers pbt
        on bm.tx_hash = pbt.tx_hash
)
-- These batches involve a token AXS (Old)
-- whose transfer function doesn't align with the emitted transfer event.
,excluded_batches as (
    select tx_hash from filtered_trades
    where 0xf5d669627376ebd411e34b98f19c868c8aba5ada in (buy_token, sell_token)
),
incoming_and_outgoing as (
    SELECT
        block_time,
        tx_hash,
        dex_swaps,
        solver_address,
        case
            when t.symbol = 'ETH' then 'WETH'
            when t.symbol is not null then t.symbol
            else cast(i.token as varchar)
        end                                     as symbol,
          case
              when token = 0xeeeeeeeeeeeeeeeeeeeeeeeeeeeeeeeeeeeeeeee
                  then 0xc02aaa39b223fe8d0a0e5c4f27ead9083c756cc2
              else token
              end                                     as token,
          case
              when receiver = 0x9008d19f58aabd9ed0d60971565aa8510560ab41
                  then amount_wei
              when sender = 0x9008d19f58aabd9ed0d60971565aa8510560ab41
                  then cast(-1 as int256) * amount_wei
              end                                     as amount,
          transfer_type
    from batch_transfers i
        left outer join tokens.erc20 t
            on i.token = t.contract_address
            and blockchain = 'ethereum'
    where tx_hash not in (select tx_hash from excluded_batches)
)
-- -- V3 PoC Query For Token List: https://dune.com/queries/2259926
,token_list as (
    SELECT from_hex(address_str) as address
    FROM ( VALUES {{TokenList}} ) as _ (address_str)
)
,block_range as (
  select min(number) as start_block,
       max(number) as end_block
  from ethereum.blocks
  where time between cast('{{StartTime}}' as timestamp) and cast('{{EndTime}}' as timestamp)
)
,internalized_imbalances as (
  select  b.block_time,
          b.tx_hash,
          b.solver_address,
          t.symbol,
          from_hex(i.token) as token,
          cast(cast(i.amount as varchar) as int256) as amount,
          'PHANTOM_TRANSFER' as transfer_type
    from cowswap.raw_internal_imbalance i
    inner join cow_protocol_ethereum.batches b
        on i.block_number = b.block_number
        and from_hex(i.tx_hash) = b.tx_hash
    join tokens.erc20 t
        on contract_address = from_hex(token)
        and blockchain = 'ethereum'
    where i.block_number between (select start_block from block_range) and (select end_block from block_range)
    and ('{{SolverAddress}}' = '0x' or b.solver_address = from_hex('{{SolverAddress}}'))
    and ('{{TxHash}}' = '0x' or b.tx_hash = from_hex('{{TxHash}}'))
)
,incoming_and_outgoing_with_internalized_imbalances as (
    select * from (
        select block_time,
              tx_hash,
              solver_address,
              symbol,
              token,
              amount,
              transfer_type
        from incoming_and_outgoing
        union all
        select * from internalized_imbalances
    ) as _
    order by block_time
)
,final_token_balance_sheet as (
    select
        solver_address,
        sum(amount) token_imbalance_wei,
        symbol,
        token,
        tx_hash,
        date_trunc('hour', block_time) as hour
    from
        incoming_and_outgoing_with_internalized_imbalances
    group by
        symbol, token, solver_address, tx_hash, block_time
    having
        sum(amount) != cast(0 as int256)
)
,token_times as (
    select hour, token
    from final_token_balance_sheet
    group by hour, token
)
,precise_prices as (
    select
        contract_address,
        decimals,
        date_trunc('hour', minute) as hour,
        avg(price) as price
    from
        prices.usd pusd
    inner join token_times tt
        on minute between date(hour) and date(hour) + interval '1' day -- query execution speed optimization since minute is indexed
        and date_trunc('hour', minute) = hour
        and contract_address = token
        and blockchain = 'ethereum'
    group by
        contract_address,
        decimals,
        date_trunc('hour', minute)
)
,intrinsic_prices as (
    select
        contract_address,
        decimals,
        hour,
        AVG(price) as price
    from (
        select
            buy_token_address as contract_address,
            ROUND(LOG(10, atoms_bought / units_bought)) as decimals,
            date_trunc('hour', block_time) as hour,
            usd_value / units_bought as price
        FROM cow_protocol_ethereum.trades
        WHERE block_time between cast('{{StartTime}}' as timestamp) and cast('{{EndTime}}' as timestamp)
        AND units_bought > 0
    UNION
        select
            sell_token_address as contract_address,
            ROUND(LOG(10, atoms_sold / units_sold)) as decimals,
            date_trunc('hour', block_time) as hour,
            usd_value / units_sold as price
        FROM cow_protocol_ethereum.trades
        WHERE block_time between cast('{{StartTime}}' as timestamp) and cast('{{EndTime}}' as timestamp)
        AND units_sold > 0
    ) as combined
    GROUP BY hour, contract_address, decimals
    order by hour
)
-- -- Price Construction: https://dune.com/queries/1579091?
,prices as (
    select
        tt.hour as hour,
        tt.token as contract_address,
        COALESCE(
            precise.decimals,
            intrinsic.decimals
        ) as decimals,
        COALESCE(
            precise.price,
            intrinsic.price
        ) as price
    from token_times tt
    LEFT JOIN precise_prices precise
        ON precise.hour = tt.hour
        AND precise.contract_address = token
    LEFT JOIN intrinsic_prices intrinsic
        ON intrinsic.hour = tt.hour
        and intrinsic.contract_address = token
)
-- -- ETH Prices: https://dune.com/queries/1578626?d=1
,eth_prices as (
    select
        date_trunc('hour', minute) as hour,
        avg(price) as eth_price
    from prices.usd
    where blockchain = 'ethereum'
    and contract_address = 0xc02aaa39b223fe8d0a0e5c4f27ead9083c756cc2
    and minute between cast('{{StartTime}}' as timestamp) and cast('{{EndTime}}' as timestamp)
    group by date_trunc('hour', minute)
)
,results_per_tx as (
    select
        ftbs.hour,
        tx_hash,
        solver_address,
        sum(cast(token_imbalance_wei as double) * price / pow(10, p.decimals)) as usd_value,
        sum(cast(token_imbalance_wei as double) * price / pow(10, p.decimals) / eth_price) * pow(10, 18) as eth_slippage_wei,
        count(*) as num_entries
    from
        final_token_balance_sheet ftbs
    left join prices p
        on token = p.contract_address
        and p.hour = ftbs.hour
    left join eth_prices ep
        on ftbs.hour = ep.hour
    group by
        ftbs.hour,
        solver_address,
        tx_hash
    having
        bool_and(price is not null)
)
,results as (
    select
        solver_address,
        concat(environment, '-', name) as solver_name,
        sum(usd_value) as usd_value,
        sum(eth_slippage_wei) as eth_slippage_wei,
        concat(
            '<a href="https://dune.com/queries/2421375?SolverAddress=',
            cast(solver_address as varchar),
            '&CTE_NAME=results_per_tx',
            '&StartTime={{StartTime}}',
            '&EndTime={{EndTime}}',
            '" target="_blank">link</a>'
        ) as batchwise_breakdown
    from
        results_per_tx rpt
    join cow_protocol_ethereum.solvers
        on address = solver_address
    group by
        solver_address,
        concat(environment, '-', name)
)
select * from {{CTE_NAME}}
