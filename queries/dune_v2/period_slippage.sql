with
filtered_trades as (
    select t.block_time,
           t.tx_hash,
           case
            when dex_swaps = 0
            -- Estimation made here: https://dune.com/queries/1646084
                then ((gas_used - 73688 - (70528 * num_trades)) / 90000)::int
                else dex_swaps
            end as dex_swaps,
           num_trades,
           solver_address,
           trader                                              as trader_in,
           receiver                                            as trader_out,
           sell_token_address                                  as sell_token,
           buy_token_address                                   as buy_token,
           atoms_sold,
           atoms_bought,
           '0x9008d19f58aabd9ed0d60971565aa8510560ab41' as contract_address
    from cow_protocol_ethereum.trades t
         join cow_protocol_ethereum.batches b
            on t.tx_hash = b.tx_hash
    where b.block_time between '{{StartTime}}' and '{{EndTime}}'
    and t.block_time between '{{StartTime}}' and '{{EndTime}}'
    and (solver_address = lower('{{SolverAddress}}') or '{{SolverAddress}}' = '0x')
    and (t.tx_hash = lower('{{TxHash}}') or '{{TxHash}}' = '0x')
),
batchwise_traders as (
    select
        tx_hash,
        collect_set(trader_in) as traders_in,
        collect_set(trader_out) as traders_out
    from filtered_trades
    group by tx_hash
),

user_in as (
    select block_time,
          tx_hash,
          dex_swaps,
          num_trades,
          solver_address,
          trader_in        as sender,
          contract_address as receiver,
          sell_token       as token,
          atoms_sold       as amount_wei,
          'IN_USER'        as transfer_type
    from filtered_trades
),
user_out as (
    select block_time,
          tx_hash,
          dex_swaps,
          num_trades,
          solver_address,
          contract_address as sender,
          trader_out       as receiver,
          buy_token        as token,
          atoms_bought     as amount_wei,
          'OUT_USER'       as transfer_type
    from filtered_trades
),
other_transfers as (
    select block_time,
          b.tx_hash,
          case
            when dex_swaps = 0
            -- Estimation made here: https://dune.com/queries/1646084
                then ((gas_used - 73688 - (70528 * num_trades)) / 90000)::int
                else dex_swaps
        end as dex_swaps,
          num_trades,
          solver_address,
          from               as sender,
          to                 as receiver,
          t.contract_address as token,
          value              as amount_wei,
          case
              when to = '0x9008d19f58aabd9ed0d60971565aa8510560ab41'
                  then 'IN_AMM'
              when from = '0x9008d19f58aabd9ed0d60971565aa8510560ab41'
                  then 'OUT_AMM'
              end            as transfer_type
    from erc20_ethereum.evt_Transfer t
             inner join cow_protocol_ethereum.batches b
                on evt_tx_hash = b.tx_hash
             inner join batchwise_traders bt
                on evt_tx_hash = bt.tx_hash
    where b.block_time between '{{StartTime}}' and '{{EndTime}}'
      and '0x9008d19f58aabd9ed0d60971565aa8510560ab41' in (to, from)
      and not array_contains(traders_in, from)
      and not array_contains(traders_out, to)
      and (t.evt_tx_hash = lower('{{TxHash}}') or '{{TxHash}}' = '0x')
      and (solver_address = lower('{{SolverAddress}}') or '{{SolverAddress}}' = '0x')
),
batch_transfers as (
    select * from user_in
    union all
    select * from user_out
    union all
    select * from other_transfers
),
-- These batches involve a token AXS (Old)
-- whose transfer function doesn't align with the emitted transfer event.
excluded_batches as (
    select tx_hash from filtered_trades
    where '0xf5d669627376ebd411e34b98f19c868c8aba5ada' in (buy_token, sell_token)
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
            else token
        end                                     as symbol,
          case
              when token = '0xeeeeeeeeeeeeeeeeeeeeeeeeeeeeeeeeeeeeeeee'
                  then '0xc02aaa39b223fe8d0a0e5c4f27ead9083c756cc2'
              else token
              end                                     as token,
          case
              when receiver = '0x9008d19f58aabd9ed0d60971565aa8510560ab41'
                  then amount_wei
              when sender = '0x9008d19f58aabd9ed0d60971565aa8510560ab41'
                  then -1 * amount_wei
              end                                     as amount,
          transfer_type
    from batch_transfers i
        left outer join tokens.erc20 t
            on i.token = t.contract_address
            and blockchain = 'ethereum'
    where tx_hash not in (select tx_hash from excluded_batches)
      -- We exclude settlements that have zero AMM interactions and settle several trades,
      -- as our query is not good enough to handle these cases accurately.
      -- Settlements with dex_swaps = 0 and num_trades = 0 can be handled in the following
      -- and we want to consider them in order to filter out illegal behaviour
      and ((dex_swaps = 0 and num_trades < 2) or dex_swaps > 0)
),
-- Benchmark takes 3 minuites to get here for ONE DAY interval!

-- Clearing Prices query here: https://dune.com/queries/1571457
pre_clearing_prices as (
    select
        call_tx_hash as tx_hash,
        price,
        token
    from gnosis_protocol_v2_ethereum.GPv2Settlement_call_settle
        lateral view posexplode(clearingPrices) as i, price
        lateral view posexplode(tokens) as j, token
    where call_block_time between '{{StartTime}}' and '{{EndTime}}'
      and call_success = true
      and i = j
),
clearing_prices as (
    select
        tx_hash,
        case
            when token = '0xeeeeeeeeeeeeeeeeeeeeeeeeeeeeeeeeeeeeeeee'
                then '0xc02aaa39b223fe8d0a0e5c4f27ead9083c756cc2'
            else token
        end as token,
        avg(price) as clearing_price
    from pre_clearing_prices
    group by tx_hash, token
),
potential_buffer_trades as (
    select block_time,
          tx_hash,
          dex_swaps,
          solver_address,
          symbol,
          token,
          sum(amount) as amount
    from incoming_and_outgoing io
    group by tx_hash,
             dex_swaps,
             solver_address,
             symbol,
             token,
             block_time
             -- exclude 0 to prevent zero division, and exclude very small values for performance
    having abs(sum(amount)) > 0.0001
),
valued_potential_buffered_trades as (
    select t.*,
          amount * clearing_price            as clearing_value,
          amount / pow(10, decimals) * price as usd_value
    from potential_buffer_trades t
    -- The following joins require the uniqueness of the prices per join,
    -- otherwise duplicated internal trades will be found.
    -- For clearing prices, it is given by construction and
    -- for prices.usd, one can see that the primary key of the table is
    -- (contract, minute) as seen here: https://dune.xyz/queries/510124
    left outer join clearing_prices cp
        on t.tx_hash = cp.tx_hash
    and t.token = cp.token
        left outer join prices.usd pusd
            on pusd.minute between '{{StartTime}}' and '{{EndTime}}'
            and pusd.contract_address = t.token
            and blockchain = 'ethereum'
            and date_trunc('minute', block_time) = pusd.minute
),
internal_buffer_trader_solvers as (
    -- See the resulting list at: https://dune.com/queries/908642
    select address
    from cow_protocol_ethereum.solvers
    -- Exclude Single Order Solvers
    where name not in (
        'Gnosis_1inch',
        'Gnosis_0x',
        'Gnosis_ParaSwap',
        'Baseline',
        'Gnosis_BalancerSOR'
    )
    -- Exclude services and test solvers
    and environment not in ('service', 'test')
),
-- V2 PoC Query For Token List: https://dune.com/queries/1576758?d=1
token_list as (
    SELECT lower(address_str) as address
  FROM (
      VALUES {{TokenList}}
    ) as _ (address_str)
),
buffer_trades as (
    Select a.block_time as block_time,
          a.tx_hash,
          a.solver_address,
          a.symbol,
          a.token       as token_from,
          b.token       as token_to,
          -1 * a.amount as amount_from,
          -1 * b.amount as amount_to,
          abs((a.clearing_value + b.clearing_value) /(abs(a.clearing_value) + abs(b.clearing_value))) as matchablity_clearing_prices,
          abs((a.usd_value + b.usd_value) / (abs(a.usd_value) + abs(b.usd_value))) as matchability_prices_dune,
          'INTERNAL_TRADE'   as transfer_type
    from valued_potential_buffered_trades a
             full outer join valued_potential_buffered_trades b
                             on a.tx_hash = b.tx_hash
    where (
              case
                  -- in order to classify as buffer trade, the positive surplus must be in an allow_listed token
                  when ((a.amount > 0 and b.amount < 0 and a.token in (select * from token_list))
                      or (b.amount > 0 and a.amount < 0 and b.token in (select * from token_list)))
                      and
                      -- We know that settlements - with at least one amm interaction - have internal buffer trades only if
                      -- the solution must come from a internal_buffer_trader_solvers solver
                      (a.solver_address in (select * from internal_buffer_trader_solvers)
                          or a.dex_swaps = 0)
                      then
                      case
                          when a.clearing_value is not null and
                              b.clearing_value is not null
                              -- If clearing prices are use, the price of internal trades are usually pretty close to
                              -- the clearing prices. But they don't have to be the same, as internal trades are usually settled
                              -- at the effective rate of an AMM. One example with deviating prices, is the tx:
                              -- 0x9a318d1abd997bcf8afed55b2946a7b1bd919d227f094cdcc99d8d6155808d7c. It
                              -- scores a matchablity of 0.021.
                              -- Another example is xd2e1eeef702d562491d6b68683772fec1b119df18e338b50f45ed4751c89e406 with a
                              -- matchablity of 0.02 for USDC to ETH trade
                              -- But for higher values, one more commonly find examples, where solvers sell a little bit too much
                              -- of the selling token and hence also receive a little bit too much of the buying token
                              -- One could see this as an internal buffer trade, but since this is not good for the protocol's buffers
                              -- we will not evaluate this as buffer trade, but rather as positive and negative slippage at the same time:
                              -- One example is: 0x63e234a1a0d657f5725817f8d829c4e14d8194fdc49b5bc09322179ff99619e7 with a matchablity of 0.26
                              -- selling too much USDC and receiving too much ETH
                              then (abs((a.clearing_value + b.clearing_value) /
                                        (abs(a.clearing_value) + abs(b.clearing_value))) <
                                    0.025
                              and a.token != b.token)
                          else
                              case
                                  when a.usd_value is not null and b.usd_value is not null
                                      -- If prices from the prices.usd dune table are used, the prices can also be off from time to time.
                                      -- On the one hand side, we don't wanna allow to high deviations. E.g. for
                                      -- 0x9a318d1abd997bcf8afed55b2946a7b1bd919d227f094cdcc99d8d6155808d7c a matchability of 0.26 is calculated
                                      -- for a slippage of WETH and the LDO deficit. (In this example the internal trade is only STRONG -> LDO)
                                      -- On the other hand, real internal trades like the CRV to USDT internal trade of 0xc15dda7c10eb317c0ad177316020ec4baa13babb0713b73480feef14045603f4
                                      -- also score a matchablilty of 0.027
                                      -- As a compromise 0.025 was chosen
                                      then (abs((a.usd_value + b.usd_value) /
                                                (abs(a.usd_value) + abs(b.usd_value))) <
                                            0.025
                                      and a.token != b.token
                                      and abs(a.usd_value) > 10 -- we don't want small slippage values to be recognized as internal swaps
                                      )
                                  else
                                      false
                                  end
                          end
                  else
                      false
                  end
              )
),
incoming_and_outgoing_with_buffer_trades as (
    select block_time,
          tx_hash,
          solver_address,
          symbol,
          token,
          amount,
          transfer_type
    from incoming_and_outgoing
    union all
    select block_time,
          tx_hash,
          solver_address,
          symbol,
          token_from as token,
          amount_from as amount,
          transfer_type
    from buffer_trades
),
final_token_balance_sheet as (
    select
        solver_address,
        sum(amount) token_imbalance_wei,
        symbol,
        token,
        tx_hash,
        date_trunc('hour', block_time) as hour
    from
        incoming_and_outgoing_with_buffer_trades
    group by
        symbol,
        token,
        solver_address,
        tx_hash,
        block_time
    having
        sum(amount) != 0
),

-- Benchmark: 4 minutes for 1 day (non-pro account)
-- select * from final_token_balance_sheet limit 10
token_times as (
    select hour, token
    from final_token_balance_sheet
    group by hour, token
),
precise_prices as (
    select
        contract_address,
        decimals,
        date_trunc('hour', minute) as hour,
        avg(price) as price
    from
        prices.usd pusd
    inner join token_times tt
        on minute between date(hour) and date(hour) + interval '1 day' -- query execution speed optimization since minute is indexed
        and date_trunc('hour', minute) = hour
        and contract_address = token
        and blockchain = 'ethereum'
    group by
        contract_address,
        decimals,
        date_trunc('hour', minute)
),
--! THIS TABLE DOES NOT EXIST ON V2 (at least not yet!)
-- median_prices as (
--     select
--         contract_address,
--         decimals,
--         tt.hour,
--         median_price
--     from
--         prices.prices_from_dex_data musd
--         inner join token_times tt on musd.hour = tt.hour
--         and contract_address = token
-- ),
intrinsic_prices as (
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
        WHERE block_time between '{{StartTime}}' and '{{EndTime}}'
        AND units_bought > 0
    UNION
        select
            sell_token_address as contract_address,
            ROUND(LOG(10, atoms_sold / units_sold)) as decimals,
            date_trunc('hour', block_time) as hour,
            usd_value / units_sold as price
        FROM cow_protocol_ethereum.trades
        WHERE block_time between '{{StartTime}}' and '{{EndTime}}'
        AND units_sold > 0
    ) as combined
    GROUP BY hour, contract_address, decimals
),
-- Price Construction: https://dune.com/queries/1579091?
prices as (
    select
        tt.hour as hour,
        tt.token as contract_address,
        COALESCE(
            precise.decimals,
            -- median.decimals,
            intrinsic.decimals
        ) as decimals,
        COALESCE(
            precise.price,
            -- median_price,
            intrinsic.price
        ) as price
    from token_times tt
    LEFT JOIN precise_prices precise
        ON precise.hour = tt.hour
        AND precise.contract_address = token
    -- LEFT JOIN prices.prices_from_dex_data median
    --     ON median.hour = tt.hour
    --     and median.contract_address = token
    LEFT JOIN intrinsic_prices intrinsic
        ON intrinsic.hour = tt.hour
        and intrinsic.contract_address = token
),
-- ETH Prices: https://dune.com/queries/1578626?d=1
eth_prices as (
    select
        date_trunc('hour', minute) as hour,
        avg(price) as eth_price
    from prices.usd
    where blockchain = 'ethereum'
    and contract_address = '0xc02aaa39b223fe8d0a0e5c4f27ead9083c756cc2'
    and minute between '{{StartTime}}' and '{{EndTime}}'
    group by date_trunc('hour', minute)
),
results_per_tx as (
    select
        ftbs.hour,
        solver_address,
        sum(token_imbalance_wei * price / pow(10, p.decimals)) as usd_value,
        sum(token_imbalance_wei * price / pow(10, p.decimals) / eth_price) * pow(10, 18) as eth_slippage_wei,
        count(*) as num_entries
    from
        final_token_balance_sheet ftbs
    left join prices p
        on token = p.contract_address
        and p.hour = ftbs.hour
    left join eth_prices ep
        on  ftbs.hour = ep.hour
    group by
        ftbs.hour,
        solver_address,
        tx_hash
    having
        bool_and(price is not null)
),
results as (
    select
        solver_address,
        concat(environment, '-', name) as solver_name,
        sum(usd_value) as usd_value,
        sum(eth_slippage_wei) as eth_slippage_wei
    from
        results_per_tx rpt
    join eth_prices ep
        on rpt.hour = ep.hour
    join cow_protocol_ethereum.solvers
        on address = solver_address
    group by
        solver_address,
        solver_name
)
select * from {{CTE_NAME}}