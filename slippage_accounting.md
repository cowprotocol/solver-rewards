# Solver Slippage Accounting

Slippage accounting is performed on a per settlement/transaction basis according to the following two primary components. 
The SQL source code can be found on 
[GitHub](https://github.com/cowprotocol/solver-rewards/blob/main/queries/dune_v2/period_slippage.sql)
or [Dune Analytics](https://dune.com/queries/3427730)

## 1. Batch-wise Token Imbalance

The token balance sheet represents a classified account of all incoming and outgoing token transfers relative to the settlement contract. 
Classification categories are `USER_{IN/OUT}`, `AMM_{IN/OUT}`.

### Transfer Type Classification

In all cases `IN` represents settlement contract as `recipient` and `OUT` as `sender`!

- `USER_{IN/OUT}` transfers are those emitted by the Settlement contract's Trade Event (with `USER_IN` adjusted for
  fees).
- `AMM_{IN/OUT}` classification is assigned to all on-chain transfers that are NOT user transfers

Note that `AMM_IN/OUT` also captures `WETH` and `sDAI` (un)wraps.

## 2. Evaluation in ETH (aka Token Prices)

Token prices are taken as the _hourly mean_ over Dune's `prices.usd` table in combination with the "intrinsic" token prices provided in settlements. 
SQL code for price table is [here](https://github.com/cowprotocol/solver-rewards/blob/d3a70f4388ef9f3345de97819b019d4754698fa6/queries/dune_v2/period_slippage.sql#L354-L436)
