-- https://github.com/cowprotocol/solver-rewards/pull/342
-- Query Here: https://dune.com/queries/3427730
with
block_range as (
    select
        min("number") as start_block,
        max("number") as end_block
    from ethereum.blocks
    where time >= cast('{{StartTime}}' as timestamp) and time < cast('{{EndTime}}' as timestamp)
)
,batch_meta as (
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
    where b.block_number >= (select start_block from block_range) and b.block_number <= (select end_block from block_range)
    and (b.solver_address = from_hex('{{SolverAddress}}') or '{{SolverAddress}}' = '0x')
    and (b.tx_hash = from_hex('{{TxHash}}') or '{{TxHash}}' = '0x')
)
,filtered_trades as (
    select t.tx_hash,
           b.block_number,
           case
                when trader = 0x9008d19f58aabd9ed0d60971565aa8510560ab41
                then 0x0000000000000000000000000000000000000000
                else trader
           end as trader_in,
           receiver                                     as trader_out,
           sell_token_address                           as sell_token,
           buy_token_address                            as buy_token,
           atoms_sold - coalesce(surplus_fee, cast(0 as uint256))        as atoms_sold,
           atoms_bought,
           0x9008d19f58aabd9ed0d60971565aa8510560ab41 as contract_address
    from cow_protocol_ethereum.trades t
         join cow_protocol_ethereum.batches b
            on t.tx_hash = b.tx_hash
    left outer join cow_protocol_ethereum.order_rewards f
        on f.tx_hash = t.tx_hash
        and f.order_uid = t.order_uid
    where b.block_number >= (select start_block from block_range) and b.block_number <= (select end_block from block_range)
    and t.block_number >= (select start_block from block_range) and t.block_number <= (select end_block from block_range)
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
    where b.block_number >= (select start_block from block_range) and b.block_number <= (select end_block from block_range)
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
    and not 0xc02aaa39b223fe8d0a0e5c4f27ead9083c756cc2 in (to, "from")
    -- ETH transfers to traders are already part of USER_OUT
    and not contains(traders_out, to)
)
-- sDAI emits only one transfer event for deposits and withdrawals.
-- This reconstructs the missing transfer from event logs.
,sdai_deposit_withdrawal_transfers as (
    -- withdraw events result in additional AMM_IN transfer
    select
        tx_hash,
        0x9008d19f58aabd9ed0d60971565aa8510560ab41 as sender,
        0x0000000000000000000000000000000000000000 as receiver,
        contract_address as token,
        cast(shares as int256) as amount_wei,
        'AMM_IN' as transfer_type
    from batch_meta bm
    join maker_ethereum.SavingsDai_evt_Withdraw w
    on w.evt_tx_hash= bm.tx_hash
    where sender = 0x9008d19f58aabd9ed0d60971565aa8510560ab41
    union all
    -- deposit events result in additional AMM_OUT transfer
    select
        tx_hash,
        0x0000000000000000000000000000000000000000 as sender,
        0x9008d19f58aabd9ed0d60971565aa8510560ab41 as receiver,
        contract_address as token,
        cast(shares as int256) as amount_wei,
        'AMM_OUT' as transfer_type
    from batch_meta bm
    join maker_ethereum.SavingsDai_evt_Deposit w
    on w.evt_tx_hash= bm.tx_hash
    where owner = 0x9008d19f58aabd9ed0d60971565aa8510560ab41
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
        union all
        select * from sdai_deposit_withdrawal_transfers
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
,incoming_and_outgoing_prelim as (
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
)
-- -- V3 PoC Query For Token List: https://dune.com/queries/2259926
,token_list as (
    SELECT from_hex(address_str) as address
    FROM ( VALUES {{TokenList}} ) as _ (address_str)
)
,incoming_and_outgoing as (
    select * from (
        select block_time,
              tx_hash,
              solver_address,
              symbol,
              token,
              amount,
              transfer_type
        from incoming_and_outgoing_prelim
    ) as _
    order by block_time
)
-- add correction for protocol fees
,raw_protocol_fee_data as (
    select
        order_uid,
        tx_hash,
        cast(cast(data.protocol_fee as varchar) as int256) as protocol_fee,
        data.protocol_fee_token as protocol_fee_token,
        cast(cast(data.surplus_fee as varchar) as int256) as surplus_fee,
        solver,
        symbol
    from cowswap.raw_order_rewards ror
    join tokens.erc20 t
        on t.contract_address = from_hex(ror.data.protocol_fee_token)
        and blockchain = 'ethereum'
    where
        block_number >= (select start_block from block_range) and block_number <= (select end_block from block_range)
        and data.protocol_fee_native_price > 0
)
,buy_token_imbalance_due_to_protocol_fee as (
    select
        t.block_time as block_time,
        from_hex(r.tx_hash) as tx_hash,
        from_hex(r.solver) as solver_address,
        symbol,
        t.buy_token_address as token,
        (-1) * r.protocol_fee as amount,
        'protocol_fee_correction' as transfer_type
    from raw_protocol_fee_data r
    join cow_protocol_ethereum.trades t
        on from_hex(r.order_uid) = t.order_uid and from_hex(r.tx_hash) = t.tx_hash
    where t.order_type='SELL'
)
,sell_token_imbalance_due_to_protocol_fee as (
    select
        t.block_time as block_time,
        from_hex(r.tx_hash) as tx_hash,
        from_hex(r.solver) as solver_address,
        symbol,
        t.sell_token_address as token,
        r.protocol_fee * (t.atoms_sold - r.surplus_fee) / t.atoms_bought as amount,
        'protocol_fee_correction' as transfer_type
    from raw_protocol_fee_data r
    join cow_protocol_ethereum.trades t
        on from_hex(r.order_uid) = t.order_uid and from_hex(r.tx_hash) = t.tx_hash
    where t.order_type='SELL'
)
-- These batches involve a token who do not emit standard transfer events.
,excluded_batches as (
    select tx_hash from filtered_trades
    where 0xf5d669627376ebd411e34b98f19c868c8aba5ada in (buy_token, sell_token) -- exclude AXS (Old)
    -- mixed ERC20/ERC721 tokens:
    or 0xf66434c34f3644473d91f065bF35225aec9e0Cfd in (buy_token, sell_token) -- exclude 404
    or 0x9E9FbDE7C7a83c43913BddC8779158F1368F0413 in (buy_token, sell_token) -- exclude PANDORA
    or 0x6C061D18D2b5bbfBe8a8D1EEB9ee27eFD544cC5D in (buy_token, sell_token) -- exclude MNRCH
    or 0xbE33F57f41a20b2f00DEc91DcC1169597f36221F in (buy_token, sell_token) -- exclude Rug
    or 0x938403C5427113C67b1604d3B407D995223C2B78 in (buy_token, sell_token) -- exclude OOZ
    or 0x54832d8724f8581e7Cc0914b3A4e70aDC0D94872 in (buy_token, sell_token) -- exclude DN404
)
,final_token_balance_sheet as (
    select
        solver_address,
        sum(amount) token_imbalance_wei,
        symbol,
        token,
        tx_hash,
        date_add('minute', (-1) * (minute(date_trunc('minute', block_time)) % {{bucket_size_in_minutes}}), date_trunc('minute', block_time)) as time_slot
    from
        incoming_and_outgoing
    where tx_hash not in (select tx_hash from excluded_batches)
    group by
        symbol, token, solver_address, tx_hash, block_time
    having
        sum(amount) != cast(0 as int256)
)
,token_times as (
    select time_slot, token
    from final_token_balance_sheet
    group by time_slot, token
)
,precise_prices as (
    select
        contract_address,
        decimals,
        date_add('minute', (-1) * (minute(pusd.minute) % {{bucket_size_in_minutes}}), pusd.minute) as time_slot,
        avg(price) as price
    from
        prices.usd pusd
    inner join token_times tt
        on minute between date(time_slot) and date(time_slot) + interval '1' day -- query execution speed optimization since minute is indexed
        and date_add('minute', (-1) * (minute(pusd.minute) % {{bucket_size_in_minutes}}), pusd.minute) = time_slot
        and contract_address = token
        and blockchain = 'ethereum'
    group by
        contract_address,
        decimals,
        date_add('minute', (-1) * (minute(pusd.minute) % {{bucket_size_in_minutes}}), pusd.minute)
)
,intrinsic_prices_prelim as (
    select
        contract_address,
        decimals,
        minute,
        AVG(price) as price
    from (
        select
            buy_token_address as contract_address,
            ROUND(LOG(10, atoms_bought / units_bought)) as decimals,
            date_trunc('minute', block_time) as minute,
            usd_value / units_bought as price
        FROM cow_protocol_ethereum.trades
        WHERE block_number >= (select start_block from block_range) and block_number <= (select end_block from block_range)
        AND units_bought > 0
    UNION
        select
            sell_token_address as contract_address,
            ROUND(LOG(10, atoms_sold / units_sold)) as decimals,
            date_trunc('minute', block_time) as minute,
            usd_value / units_sold as price
        FROM cow_protocol_ethereum.trades
        WHERE block_number >= (select start_block from block_range) and block_number <= (select end_block from block_range)
        AND units_sold > 0
    ) as combined
    GROUP BY minute, contract_address, decimals
    order by minute
)
,intrinsic_prices as (
    select
        contract_address,
        decimals,
        date_add('minute', (-1) * (minute(minute) % {{bucket_size_in_minutes}}), minute) as time_slot,
        AVG(price) as price
    from
    intrinsic_prices_prelim
    group by date_add('minute', (-1) * (minute(minute) % {{bucket_size_in_minutes}}), minute), contract_address, decimals
    order by date_add('minute', (-1) * (minute(minute) % {{bucket_size_in_minutes}}), minute)
)
-- -- Price Construction: https://dune.com/queries/1579091?
,prices as (
    select
        tt.time_slot as time_slot,
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
        ON precise.time_slot = tt.time_slot
        AND precise.contract_address = token
    LEFT JOIN intrinsic_prices intrinsic
        ON intrinsic.time_slot = tt.time_slot
        and intrinsic.contract_address = token
)
-- -- ETH Prices: https://dune.com/queries/1578626?d=1
,eth_prices as (
    select
        date_add('minute', (-1) * (minute(minute) % {{bucket_size_in_minutes}}), minute) as time_slot,
        avg(price) as eth_price
    from prices.usd
    where blockchain = 'ethereum'
    and contract_address = 0xc02aaa39b223fe8d0a0e5c4f27ead9083c756cc2
    and minute between cast('{{StartTime}}' as timestamp) and cast('{{EndTime}}' as timestamp)
    group by date_add('minute', (-1) * (minute(minute) % {{bucket_size_in_minutes}}), minute)
)
,results_per_tx as (
    select
        ftbs.time_slot,
        tx_hash,
        solver_address,
        sum(cast(token_imbalance_wei as double) * price / pow(10, p.decimals)) as usd_value,
        sum(cast(token_imbalance_wei as double) * price / pow(10, p.decimals) / eth_price) * pow(10, 18) as eth_slippage_wei,
        count(*) as num_entries
    from
        final_token_balance_sheet ftbs
    left join prices p
        on token = p.contract_address
        and p.time_slot = ftbs.time_slot
    left join eth_prices ep
        on ftbs.time_slot = ep.time_slot
    group by
        ftbs.time_slot,
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
            '<a href="https://dune.com/queries/3427730?SolverAddress=',
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
