with
-- This subquery is not executable on its own.
filtered_trades as (
    select t.block_time,
           t.tx_hash,
           dex_swaps,
           num_trades,
           solver_name,
           solver_address,
           trader                                                as trader_in,
           receiver                                              as trader_out,
           sell_token_address                                    as "sellToken",
           buy_token_address                                     as "buyToken",
           atoms_sold                                            as "sellAmount",
           atoms_bought                                          as "buyAmount",
           '\x9008D19f58AAbD9eD0D60971565AA8510560ab41' :: bytea as contract_address
    from gnosis_protocol_v2."trades" t
             join gnosis_protocol_v2."view_batches" b on t.tx_hash = b.tx_hash
    where b.block_time between '{{StartTime}}'
        and '{{EndTime}}'
      and case
              when '{{TxHash}}' = '0x' then true
              else replace('{{TxHash}}', '0x', '\x') :: bytea = t.tx_hash
        end
),
user_in as (
    select block_time,
           tx_hash,
           dex_swaps,
           num_trades,
           solver_address,
           solver_name,
           trader_in        as sender,
           contract_address as receiver,
           "sellToken"      as token,
           "sellAmount"     as amount_wei,
           'IN_USER'        as transfer_type
    from filtered_trades
),
user_out as (
    select block_time,
           tx_hash,
           dex_swaps,
           num_trades,
           solver_address,
           solver_name,
           contract_address as sender,
           trader_out       as receiver,
           "buyToken"       as token,
           "buyAmount"      as amount_wei,
           'OUT_USER'       as transfer_type
    from filtered_trades
),
other_transfers as (
    select block_time,
           tx_hash,
           dex_swaps,
           num_trades,
           solver_address,
           solver_name,
           "from"                sender,
           "to"                  receiver,
           t.contract_address as token,
           value              as amount_wei,
           case
               when "to" = '\x9008D19f58AAbD9eD0D60971565AA8510560ab41' -- beta contract
                   then 'IN_AMM'
               when "from" = '\x9008D19f58AAbD9eD0D60971565AA8510560ab41' -- beta contract
                   then 'OUT_AMM'
               end            as transfer_type
    from erc20."ERC20_evt_Transfer" t
             inner join gnosis_protocol_v2."view_batches" b
                        on evt_tx_hash = tx_hash
    where b.block_time between '{{StartTime}}'
        and '{{EndTime}}'
      and '\x9008D19f58AAbD9eD0D60971565AA8510560ab41' in ("to", "from")
      and "from" not in (
        select trader_in
        from filtered_trades
    )
      and "to" not in (
        select trader_out
        from filtered_trades
    )
      and case
              when '{{TxHash}}' = '0x' then true
              else replace('{{TxHash}}', '0x', '\x') :: bytea = b.tx_hash
        end
),
batch_transfers as (
    select *
    from user_in
    union
        all
    select *
    from user_out
    union
        all
    select *
    from other_transfers
),
-- These batches involve a token AXS (Old)
-- whose transfer function doesn't align with the emitted transfer event.
exluded_batches as (
    select tx_hash
    from filtered_trades
    where '\xf5d669627376ebd411e34b98f19c868c8aba5ada'
              in ("buyToken", "sellToken")
),
incoming_and_outgoing as (
    SELECT block_time,
           tx_hash,
           dex_swaps,
           CONCAT('0x', ENCODE(solver_address, 'hex')) as solver_address,
           solver_name,
           case
               when t.symbol = 'ETH' then 'WETH'
               when t.symbol is not null then t.symbol
               else text(token)
               end                                     as symbol,
           case
               when token = '\xeeeeeeeeeeeeeeeeeeeeeeeeeeeeeeeeeeeeeeee'
                   then '\xc02aaa39b223fe8d0a0e5c4f27ead9083c756cc2'
               else token
               end                                     as token,
           case
               when receiver =
                    '\x9008D19f58AAbD9eD0D60971565AA8510560ab41' -- beta contract
                   then amount_wei
               when sender = '\x9008D19f58AAbD9eD0D60971565AA8510560ab41' -- beta contract
                   then -1 * amount_wei
               end                                     as amount,
           transfer_type
    from batch_transfers i
             left outer join erc20.tokens t on i.token = t.contract_address
        where 
         -- We exclude settlements that have zero AMM interactions and settle several trades,
         -- as our query is not good enough to handle these cases accurately.
         -- Settlements with dex_swaps = 0 and num_trades = 0 can be handled in the following
         -- and we want to consider them in order to filter out illegal behaviour
          (dex_swaps = 0 and num_trades < 2) or dex_swaps > 0
            
    and tx_hash not in (select tx_hash from exluded_batches)
),
pre_clearing_prices as (
    select call_tx_hash             as tx_hash,
           unnest("clearingPrices") as price,
           unnest(tokens)           as token
    from gnosis_protocol_v2."GPv2Settlement_call_settle"
    where call_success = true
      and call_block_time between '{{StartTime}}'
        and '{{EndTime}}'
    order by call_block_number desc
),
clearing_prices as (
    select tx_hash,
           case
               when token = '\xeeeeeeeeeeeeeeeeeeeeeeeeeeeeeeeeeeeeeeee'
                   then '\xc02aaa39b223fe8d0a0e5c4f27ead9083c756cc2'
               else token
               end as token,
           avg(price) as clearing_price
    from pre_clearing_prices
    group by 1,2
),
potential_buffer_trades as (
    select block_time,
           tx_hash,
           dex_swaps,
           solver_address,
           solver_name,
           symbol,
           token,
           sum(amount) as amount
    from incoming_and_outgoing io
    group by tx_hash,
             dex_swaps,
             solver_address,
             solver_name,
             symbol,
             token,
             block_time
             -- exclude 0 to prevent zero division, and exclude very small values for performance
    having abs(sum(amount)) > 0.0001
),
valued_potential_buffered_trades as (
    select t.*,
           amount * clearing_price        as clearing_value,
           amount / 10 ^ decimals * price as usd_value
    from potential_buffer_trades t
            -- The following joins require the uniqueness of the prices per join,
            -- otherwise duplicated internal trades will be found.
            -- For clearing prices, it is given by construction and 
            -- for prices.usd, one can see that the primary key of the table is 
            -- (contract, minute) as seen here: https://dune.xyz/queries/510124
             left outer join clearing_prices cp on t.tx_hash = cp.tx_hash
        and t.token = cp.token
             left outer join prices.usd pusd
                             on pusd.contract_address = t.token
                                 and date_trunc('minute', block_time) = pusd.minute
),
internal_buffer_trader_solvers as (
    Select 
    CONCAT('0x', ENCODE(address, 'hex')) 
    from gnosis_protocol_v2."view_solvers" 
    where 
        name = 'DexCowAgg' or
        name = 'CowDexAg' or 
        name = 'MIP' or
        name = 'Quasimodo' or
        name = 'QuasiModo'
),
buffer_trades as (
    Select date(a.block_time) as block_time,
           a.tx_hash,
           a.solver_address,
           a.solver_name,
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
                -- in order to classify as buffer trade, the postive surplus must be in an allow_listed token
                when ((a.amount > 0 and b.amount < 0 and a.token in (Select * from allow_listed_tokens)) 
                    or (b.amount > 0 and a.amount < 0 and b.token in (Select * from allow_listed_tokens)))
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
                            -- we will not evalute this as buffer trade, but rather as positive and negative slippage at the same time:
                            -- One example is: 0x63e234a1a0d657f5725817f8d829c4e14d8194fdc49b5bc09322179ff99619e7 with a matchablity of 0.26
                            -- selling too much usdc and receiving too much eth
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
                                        -- On the other hand side, real internal trades like the CRV to USDT internal trade of 0xc15dda7c10eb317c0ad177316020ec4baa13babb0713b73480feef14045603f4
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
           solver_name,
           symbol,
           token as token,
           amount as amount,
           transfer_type
    from incoming_and_outgoing
    union
        all
    select block_time,
           tx_hash,
           solver_address,
           solver_name,
           symbol,
           token_from as token,
           amount_from as amount,
           transfer_type
    from buffer_trades
),
final_token_balance_sheet as (
    select solver_address,
           solver_name,
           sum(amount) token_imbalance_wei,
           symbol,
           token,
           tx_hash
    from incoming_and_outgoing_with_buffer_trades
    group by symbol,
             token,
             solver_address,
             solver_name,
             tx_hash
),
end_prices as (
    select median_price as price,
           p_complete.contract_address,
           decimals
    from prices.prices_from_dex_data p_complete
    where p_complete.hour = '{{EndTime}}'
),
results_per_tx as (
    select solver_address,
           solver_name,
           sum(token_imbalance_wei * price / 10 ^ p.decimals) as usd_value,
           tx_hash
    from final_token_balance_sheet
             inner join end_prices p on token = p.contract_address
    group by solver_address,
             solver_name,
             tx_hash
    having sum(token_imbalance_wei) != 0
),
results as (
    select solver_address,
           solver_name,
           sum(usd_value) as usd_value
    from results_per_tx
    group by solver_address, solver_name
),
eth_price as (
    select price
    from prices."layer1_usd_eth"
    where minute = '{{EndTime}}'
)
