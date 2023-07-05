# Internal Transfers

## Motivation & Summary

Internal Settlements have been a challenge to evaluate slippage since some information
required for the computation never winds up on chain.
Specifically, when the driver decides to internalize an interaction provided by a solver,
the interaction is excluded from the settlement call data.
In order to recover this data we must make token transfers (or imbalances) from
internalized interactions transparently available for consumption.

This project replaces the subquery
[buffer_trades](https://github.com/cowprotocol/solver-rewards/blob/c7e9c85706decb1a1be28d639ee34e35646bca50/queries/dune_v2/period_slippage.sql#L239-L309)
(an approximation for internal interactions implemented purely within Dune Analytics) with the actual internalized data.

In brief, the project consists of a Data Pipeline implementing the following flow;

1. WebHook/Event Listener for CoW Protocol Settlement Events emitted
   by [CoW Protocol: GPv2Settlement](https://etherscan.io/address/0x9008d19f58aabd9ed0d60971565aa8510560ab41)
2. Settlement Events trigger an ETL Pipeline that
    - Fetches full/unoptimized call data provided by the solver for the winning settlement from
      the [Orderbook API](https://api.cow.fi/docs/#)
    - Simulates the full call data extracting and classifying transfers from event logs
    - Evaluates the `InternalizedLedger` as the difference `FullLedger - ActualLedger`
3. Finally, the `InternalizedLedger` from step 2 is written to a [Database](./database/README.md) and later synced into
   Dune community sources.

For more Details on each component outlined above please visit respective readmes:

## [Webhook] Tenderly Actions

Documentation: https://tenderly.co/web3-actions
Requirements: [Tenderly CLI](https://github.com/Tenderly/tenderly-cli)

actions directory was scaffolded and deployed as follows:

```shell
tenderly actions init --language typescript
tenderly actions deploy
```

## Generate Database Schema

Following this article on [Postgres with Typescript](https://www.atdatabases.org/docs/pg-guide-typescript) we can
generate the schema
From within `actions/`

```shell
source 
 export DB_URL=postgresql://${POSTGRES_USER}:${POSTGRES_PASSWORD}@${POSTGRES_HOST}:${POSTGRES_PORT}/${POSTGRES_DB}
npx @databases/pg-schema-cli --database $DB_URL --directory src/__generated__
```